// Phase 2: Damage calc wrapper.
// Reads a single JSON request from stdin, prints a single JSON result to stdout.
// On error, exits 1 and writes a structured JSON error to stderr.
//
// Input schema (all keys optional unless marked required):
// {
//   "gen": 9,                                    // required, 1-9
//   "format": "Singles",                         // "Singles" | "Doubles", default "Singles"
//   "attacker": {
//     "name": "Garchomp",                        // required, English Showdown name
//     "level": 50,                               // default 100
//     "item": "Choice Band",
//     "ability": "Rough Skin",
//     "nature": "Jolly",
//     "evs": { "hp": 0, "atk": 252, "def": 0, "spa": 0, "spd": 0, "spe": 252 },
//     "ivs": { "hp": 31, "atk": 31, ... },
//     "boosts": { "atk": 1 },
//     "status": "brn" | "psn" | "tox" | "par" | "slp" | "frz" | "",
//     "teraType": "Ground",                      // optional
//     "isDynamaxed": true,                       // gen 8 only
//     "dynamaxLevel": 10,
//     "abilityOn": true                          // for activation-required abilities
//   },
//   "defender": { ... same shape },
//   "move": {
//     "name": "Earthquake",                      // required
//     "isCrit": false,
//     "useZ": false,
//     "useMax": false,
//     "hits": 1,                                 // for multi-hit override
//     "bp": 100                                  // override base power
//   },
//   "field": {
//     "weather": "Sun" | "Rain" | "Sand" | "Snow" | "Hail" | "Harsh Sunshine" | "Heavy Rain" | "Strong Winds",
//     "terrain": "Electric" | "Grassy" | "Misty" | "Psychic",
//     "isGravity": false,
//     "isMagicRoom": false,
//     "isWonderRoom": false,
//     "attackerSide": { "isSR": false, "isReflect": false, "isLightScreen": false, ... },
//     "defenderSide": { "isSR": true, "spikes": 0, ... }
//   }
// }
//
// Output schema:
// {
//   "ok": true,
//   "damage": [n0, n1, ..., n15],
//   "min": number, "max": number,
//   "percent_min": number, "percent_max": number,
//   "ko_chance": { "chance": number, "n": number, "text": string },
//   "desc": string,
//   "attacker_stats": StatsTable, "defender_stats": StatsTable,
//   "elapsed_ms": number
// }

import { Generations, Pokemon, Move, Field, calculate } from "@smogon/calc";

// v0.6.0 Bug A fix: Aegislash species normalization.
// P6 conclusion: Among 26 forme-switching species, only Aegislash is unregistered
// in @smogon/calc v0.11.0 when the suffix is omitted. The other 25 (Mimikyu,
// Wishiwashi, Greninja, Lycanroc, Zygarde, Urshifu, Basculegion, Palafin,
// Ogerpon, Calyrex, etc.) all resolve correctly without a forme suffix.
// Aegislash → Aegislash-Shield (Stance Change default shield form,
// HP60/Atk50/Def140/SpA50/SpD140/Spe60).
const NORMALIZE_SPECIES: Record<string, string> = Object.freeze({
  "Aegislash": "Aegislash-Shield",
});

function normalizeSpeciesName(name: string): string {
  if (typeof name !== "string") return name;
  // Use hasOwnProperty to prevent prototype pollution lookups.
  if (Object.prototype.hasOwnProperty.call(NORMALIZE_SPECIES, name)) {
    const normalized = NORMALIZE_SPECIES[name];
    process.stderr.write(
      `[WARN] Pokemon name '${name}' normalized to '${normalized}' (default Stance Change form). ` +
        `Specify '${name}-Blade' or '${name}-Shield' explicitly to suppress.\n`,
    );
    return normalized;
  }
  return name;
}

type StatsTable = { hp: number; atk: number; def: number; spa: number; spd: number; spe: number };

interface SideInput {
  isSR?: boolean;
  spikes?: number;
  isReflect?: boolean;
  isLightScreen?: boolean;
  isAuroraVeil?: boolean;
  isProtected?: boolean;
  isSeeded?: boolean;
  isFriendGuard?: boolean;
  isHelpingHand?: boolean;
  isTailwind?: boolean;
  isFlowerGift?: boolean;
  isBattery?: boolean;
  isPowerSpot?: boolean;
  isSteelySpirit?: boolean;
}

interface PokemonInput {
  name: string;
  level?: number;
  item?: string;
  ability?: string;
  nature?: string;
  evs?: Partial<StatsTable>;
  ivs?: Partial<StatsTable>;
  // Champions-accurate path: pass the in-game 実数値 (final Lv50 stats, as shown by
  // "ダメ系プラス" / the in-game summary) directly. When present, these OVERRIDE the
  // evs/ivs/nature computation. Champions has NO 510 EV total cap, so EV-reconstruction
  // is lossy; rawStats is the source of truth. Provide all 6 (hp/atk/def/spa/spd/spe).
  rawStats?: Partial<StatsTable>;
  boosts?: Partial<Omit<StatsTable, "hp">>;
  status?: "brn" | "psn" | "tox" | "par" | "slp" | "frz" | "";
  teraType?: string;
  isDynamaxed?: boolean;
  dynamaxLevel?: number;
  abilityOn?: boolean;
  curHP?: number;
}

interface MoveInput {
  name: string;
  isCrit?: boolean;
  useZ?: boolean;
  useMax?: boolean;
  hits?: number;
  bp?: number;
  type?: string;
}

interface FieldInput {
  weather?: string;
  terrain?: string;
  isGravity?: boolean;
  isMagicRoom?: boolean;
  isWonderRoom?: boolean;
  attackerSide?: SideInput;
  defenderSide?: SideInput;
}

interface CalcInput {
  gen: number;
  format?: "Singles" | "Doubles";
  attacker: PokemonInput;
  defender: PokemonInput;
  move: MoveInput;
  field?: FieldInput;
}

function readStdin(): Promise<string> {
  return new Promise((resolve, reject) => {
    let buf = "";
    process.stdin.setEncoding("utf-8");
    process.stdin.on("data", (chunk) => (buf += chunk));
    process.stdin.on("end", () => resolve(buf));
    process.stdin.on("error", reject);
  });
}

// v0.9.0: given a desired final stat value, find the baseStat that reproduces it
// with EV=0 / IV=31 / neutral nature at the given level. @smogon/calc's damage
// formula reads `rawStats` (recomputed from baseStats+evs+nature on every clone),
// so injecting `.stats`/`.rawStats` post-construction is silently discarded by
// calculate()'s internal clone. The robust path is to override `species.baseStats`
// (which clone() preserves via `overrides: this.species`) so calcStat() yields the
// exact in-game 実数値. This makes the calc Champions-accurate even though Champions
// has NO 510 EV total cap (so EV-reconstruction would be lossy/impossible).
function baseStatForTarget(stat: keyof StatsTable, target: number, level: number): number {
  const iv = 31;
  // Shedinja-style fixed 1 HP (calc treats baseHP===1 specially).
  if (stat === "hp" && target <= 1) return target <= 0 ? 0 : 1;
  // Find the base that reproduces `target` exactly; if none (parity gap at higher
  // levels, or target out of the 0-255 reachable range), return the CLOSEST base so
  // the error degrades gracefully to ±1 rather than clamping to a wildly wrong value.
  let bestB = 0;
  let bestDiff = Infinity;
  for (let b = 0; b <= 255; b++) {
    const inner = Math.floor(((2 * b + iv) * level) / 100);
    const v = stat === "hp" ? inner + level + 10 : inner + 5; // neutral nature, EV 0
    if (v === target) return b;
    const diff = Math.abs(v - target);
    if (diff < bestDiff) {
      bestDiff = diff;
      bestB = b;
    }
  }
  return bestB;
}

function buildPokemon(gen: ReturnType<typeof Generations.get>, p: PokemonInput): Pokemon {
  if (!p.name) throw new Error("attacker/defender.name required");
  const opts: Record<string, unknown> = {};
  const level = p.level !== undefined ? p.level : 100;
  if (p.level !== undefined) opts.level = p.level;
  if (p.item) opts.item = p.item;
  if (p.ability) opts.ability = p.ability;
  if (p.boosts) opts.boosts = p.boosts;
  if (p.status !== undefined) opts.status = p.status;
  if (p.teraType) opts.teraType = p.teraType;
  if (p.isDynamaxed) opts.isDynamaxed = p.isDynamaxed;
  if (p.dynamaxLevel !== undefined) opts.dynamaxLevel = p.dynamaxLevel;
  if (p.abilityOn !== undefined) opts.abilityOn = p.abilityOn;
  if (p.curHP !== undefined) opts.curHP = p.curHP;

  const speciesName = normalizeSpeciesName(p.name);

  if (p.rawStats) {
    // Champions-accurate path: reproduce exact 実数値 via baseStats override.
    // Ignore evs/ivs/nature (they would perturb the target); leave defaults
    // (EV 0 / IV 31 / neutral) so calcStat() returns the target verbatim.
    // The reverse-derivation uses the gen 3+ ADV stat formula — guard older gens.
    const genNum = (gen as { num?: number }).num;
    if (genNum !== undefined && genNum < 3) {
      throw new Error("rawStats is only supported for gen 3+ (ADV stat formula)");
    }
    opts.level = level; // pin level so the derivation and Pokemon agree
    const speciesId = speciesName.toLowerCase().replace(/[^a-z0-9]/g, "");
    const speciesDef = (gen as { species: { get: (id: string) => { baseStats?: StatsTable } | undefined } })
      .species.get(speciesId);
    if (!speciesDef || !speciesDef.baseStats) {
      throw new Error(`Unknown species for rawStats: ${speciesName}`);
    }
    const overriddenBase: StatsTable = { ...speciesDef.baseStats };
    const keys: (keyof StatsTable)[] = ["hp", "atk", "def", "spa", "spd", "spe"];
    for (const k of keys) {
      const tgt = p.rawStats[k];
      if (tgt !== undefined) overriddenBase[k] = baseStatForTarget(k, tgt, level);
    }
    opts.overrides = { baseStats: overriddenBase };
    return new Pokemon(gen, speciesName, opts);
  }

  if (p.nature) opts.nature = p.nature;
  if (p.evs) opts.evs = p.evs;
  if (p.ivs) opts.ivs = p.ivs;
  return new Pokemon(gen, speciesName, opts);
}

function buildMove(gen: ReturnType<typeof Generations.get>, m: MoveInput): Move {
  if (!m.name) throw new Error("move.name required");
  const opts: Record<string, unknown> = {};
  if (m.isCrit !== undefined) opts.isCrit = m.isCrit;
  if (m.useZ !== undefined) opts.useZ = m.useZ;
  if (m.useMax !== undefined) opts.useMax = m.useMax;
  if (m.hits !== undefined) opts.hits = m.hits;
  if (m.bp !== undefined) opts.bp = m.bp;
  if (m.type) opts.type = m.type;
  return new Move(gen, m.name, opts);
}

function buildField(f: FieldInput | undefined): Field {
  if (!f) return new Field();
  const opts: Record<string, unknown> = {};
  if (f.weather) opts.weather = f.weather;
  if (f.terrain) opts.terrain = f.terrain;
  if (f.isGravity) opts.isGravity = f.isGravity;
  if (f.isMagicRoom) opts.isMagicRoom = f.isMagicRoom;
  if (f.isWonderRoom) opts.isWonderRoom = f.isWonderRoom;
  if (f.attackerSide) opts.attackerSide = f.attackerSide;
  if (f.defenderSide) opts.defenderSide = f.defenderSide;
  return new Field(opts);
}

function summarize(input: CalcInput): Record<string, unknown> {
  const t0 = performance.now();
  const gens = Generations.get(input.gen);

  const attacker = buildPokemon(gens, input.attacker);
  const defender = buildPokemon(gens, input.defender);
  const move = buildMove(gens, input.move);
  const field = buildField(input.field);

  const result = calculate(gens, attacker, defender, move, field);

  // damage may be number, number[], or array of arrays for multi-hit.
  // Normalize to flat number[].
  let damage: number[] = [];
  const raw = result.damage as number | number[] | number[][];
  if (Array.isArray(raw)) {
    if (raw.length > 0 && Array.isArray(raw[0])) {
      // multi-hit -> use last (post-hits cumulative is not given; flatten and report
      // each hit's roll set so caller can interpret).
      damage = (raw as number[][]).flat();
    } else {
      damage = raw as number[];
    }
  } else if (typeof raw === "number") {
    damage = [raw];
  }

  const hp = defender.maxHP();
  const min = damage.length > 0 ? Math.min(...damage) : 0;
  const max = damage.length > 0 ? Math.max(...damage) : 0;
  const percentMin = hp > 0 ? +((min / hp) * 100).toFixed(1) : 0;
  const percentMax = hp > 0 ? +((max / hp) * 100).toFixed(1) : 0;

  // v0.6.0 Bug B fix: 0-damage rolls trigger an assertion inside @smogon/calc's
  // getKOChance() (e.g. Poltergeist/Fling without item, Trick/Magic Room status
  // moves). result.fullDesc() also calls getKOChance internally, so both paths
  // must be short-circuited with structured fallback values instead of throwing.
  const isZeroDamage =
    damage.length === 0 || damage[damage.length - 1] === 0;
  const zeroDamageKoText =
    "no damage (move conditions not met: e.g., Poltergeist/Fling requires item, Trick/Magic Room are status moves)";
  const ko = isZeroDamage
    ? { chance: 0, n: 0, text: zeroDamageKoText }
    : result.kochance
    ? result.kochance()
    : { chance: 0, n: 0, text: "" };
  let desc: string;
  if (isZeroDamage) {
    // Build a minimal description that mirrors the @smogon/calc format without
    // invoking fullDesc() (which would call getKOChance and throw).
    const atkName = input.attacker.name;
    const defName = input.defender.name;
    const moveName = input.move.name;
    desc = `${atkName} ${moveName} vs. ${defName}: 0-0 (0 - 0%) -- ${zeroDamageKoText}`;
  } else {
    desc = result.fullDesc ? result.fullDesc() : "";
  }
  const elapsedMs = +(performance.now() - t0).toFixed(2);

  return {
    ok: true,
    damage,
    min,
    max,
    percent_min: percentMin,
    percent_max: percentMax,
    defender_max_hp: hp,
    ko_chance: ko,
    desc,
    attacker_stats: attacker.stats,
    defender_stats: defender.stats,
    elapsed_ms: elapsedMs,
  };
}

async function main() {
  const raw = await readStdin();
  const input = JSON.parse(raw) as CalcInput;
  const result = summarize(input);
  process.stdout.write(JSON.stringify(result));
  process.exit(0);
}

main().catch((err: Error) => {
  const errOut = {
    ok: false,
    error: err.message,
    stack: err.stack,
  };
  process.stderr.write(JSON.stringify(errOut));
  process.exit(1);
});
