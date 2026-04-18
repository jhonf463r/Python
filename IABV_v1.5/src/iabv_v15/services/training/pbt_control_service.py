from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import random
from typing import Any


class PBTControlService:
    def __init__(self, models_dir: str) -> None:
        self.base_dir = Path(models_dir) / 'pbt_runs'
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.latest_path = self.base_dir / 'latest_run.json'

    def load_state(self) -> dict[str, Any]:
        if self.latest_path.exists():
            return json.loads(self.latest_path.read_text(encoding='utf-8'))
        return {
            'generation': 0,
            'best_score': 0.0,
            'summary': 'Sin ejecuciones PBT aun. La base esta lista para explorar configuraciones.',
            'updated_at_utc': '',
            'checkpoint_path': '',
            'candidates': [],
            'source_modules': ['scheduler', 'selector', 'mutator', 'local_backend'],
        }

    def run_cycle(self, metrics: dict[str, int]) -> dict[str, Any]:
        previous = self.load_state()
        generation = int(previous.get('generation', 0)) + 1
        rng = random.Random(self._seed_value(generation, metrics))
        base_population = self._build_population(generation, metrics, previous.get('candidates', []), rng)
        scored = [self._score_candidate(candidate, metrics, rng) for candidate in base_population]
        ranked = sorted(scored, key=lambda item: item['score'], reverse=True)
        best = ranked[0]
        checkpoint = {
            'generation': generation,
            'best_score': best['score'],
            'summary': (
                f'Generacion {generation} completada. Mejor configuracion {best["candidate_id"]} '
                f'con score {best["score"]}. Inspirado en scheduler, selector y mutacion de IABV 1.3.'
            ),
            'updated_at_utc': datetime.now(timezone.utc).isoformat(),
            'checkpoint_path': '',
            'candidates': ranked,
            'source_modules': ['scheduler', 'selector', 'mutator', 'local_backend'],
            'metrics': metrics,
        }
        checkpoint_path = self.base_dir / f'generation_{generation:03d}.json'
        checkpoint['checkpoint_path'] = str(checkpoint_path)
        payload = json.dumps(checkpoint, ensure_ascii=False, indent=2)
        checkpoint_path.write_text(payload, encoding='utf-8')
        self.latest_path.write_text(payload, encoding='utf-8')
        return checkpoint

    def _seed_value(self, generation: int, metrics: dict[str, int]) -> int:
        return (
            generation * 997
            + metrics.get('episodes', 0) * 37
            + metrics.get('knowledge', 0) * 19
            + metrics.get('artifacts', 0) * 11
            + metrics.get('runs', 0) * 7
        )

    def _build_population(
        self,
        generation: int,
        metrics: dict[str, int],
        previous_candidates: list[dict[str, Any]],
        rng: random.Random,
    ) -> list[dict[str, Any]]:
        population: list[dict[str, Any]] = []
        seeds = previous_candidates[:2] if previous_candidates else []
        for index in range(4):
            if index < len(seeds):
                candidate = self._mutate_candidate(seeds[index], generation, index + 1, rng)
            else:
                candidate = {
                    'candidate_id': f'g{generation}-c{index + 1}',
                    'learning_rate': round(rng.uniform(0.018, 0.085), 4),
                    'mutation_rate': round(rng.uniform(0.08, 0.28), 3),
                    'exploration_bias': round(rng.uniform(0.24, 0.88), 3),
                    'stability_bias': round(rng.uniform(0.35, 0.92), 3),
                }
            candidate['context_signal'] = metrics.get('episodes', 0) + metrics.get('knowledge', 0)
            population.append(candidate)
        return population

    def _mutate_candidate(self, candidate: dict[str, Any], generation: int, slot: int, rng: random.Random) -> dict[str, Any]:
        return {
            'candidate_id': f'g{generation}-c{slot}',
            'learning_rate': round(max(0.01, min(0.11, candidate.get('learning_rate', 0.04) + rng.uniform(-0.01, 0.01))), 4),
            'mutation_rate': round(max(0.04, min(0.35, candidate.get('mutation_rate', 0.16) + rng.uniform(-0.03, 0.03))), 3),
            'exploration_bias': round(max(0.15, min(0.95, candidate.get('exploration_bias', 0.5) + rng.uniform(-0.08, 0.08))), 3),
            'stability_bias': round(max(0.2, min(0.98, candidate.get('stability_bias', 0.6) + rng.uniform(-0.08, 0.08))), 3),
        }

    def _score_candidate(
        self,
        candidate: dict[str, Any],
        metrics: dict[str, int],
        rng: random.Random,
    ) -> dict[str, Any]:
        signal = (
            min(metrics.get('episodes', 0), 20) * 0.6
            + min(metrics.get('knowledge', 0), 20) * 0.8
            + min(metrics.get('artifacts', 0), 40) * 0.25
            + min(metrics.get('runs', 0), 30) * 0.15
        )
        lr_score = max(0.0, 1.0 - abs(candidate['learning_rate'] - 0.045) / 0.05)
        mutation_score = max(0.0, 1.0 - abs(candidate['mutation_rate'] - 0.16) / 0.2)
        exploration_score = candidate['exploration_bias'] * 0.55 + candidate['stability_bias'] * 0.45
        score = round(signal + lr_score * 18 + mutation_score * 12 + exploration_score * 20 + rng.uniform(-1.5, 1.5), 2)
        notes = (
            'Balancea exploracion y estabilidad con checkpoints ligeros. '
            'Pensado para aprovechar la base de PBT de IABV 1.3 sin importar codigo legacy en runtime.'
        )
        return {**candidate, 'score': score, 'notes': notes}
