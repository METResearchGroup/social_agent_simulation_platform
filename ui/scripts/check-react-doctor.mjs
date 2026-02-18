/**
 * React Doctor score gate: exit 1 if score is below REACT_DOCTOR_MIN_SCORE (default 70).
 * Run from ui/ directory: node scripts/check-react-doctor.mjs
 */
import { diagnose } from "react-doctor/api";

const minScore = Number(process.env.REACT_DOCTOR_MIN_SCORE, 10) || 70;
const result = await diagnose(".", { lint: true, deadCode: true });

if (result?.score?.score == null) {
  console.error("React Doctor: could not compute score (result or score missing).");
  process.exit(1);
}

const { score: value, label } = result.score;
if (value < minScore) {
  console.error(
    `React Doctor score ${value} (${label}) is below minimum ${minScore}. Fix diagnostics and re-run.`
  );
  process.exit(1);
}

console.log(`React Doctor score ${value} (${label}) meets minimum ${minScore}.`);
process.exit(0);
