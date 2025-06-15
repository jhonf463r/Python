import os
import sqlite3
import pandas as pd
import numpy as np

class DataCleaner:
    """
    Limpia y enriquece registros de ruleta desde SQLite o CSV,
    asegurando que 'numero' no tenga NaNs y contando runs (ausencias)
    para cada categoría: rojo, negro, par, impar, 1-18, 19-36 y cero.
    """
    # Incluimos "cero" para rastrear runs de ceros
    CATEGORIES = ["rojo", "negro", "par", "impar", "1-18", "19-36", "cero"]

    def __init__(
        self,
        raw_src: str = "database/ruleta_stats.db",
        clean_csv: str = "data/clean_records.csv",
        min_interval: float = 0.1,
        accel_window: int = 5,
        player_window: int = 10,
        strategy_window: int = 20
    ):
        self.raw_src         = raw_src
        self.clean_csv       = clean_csv
        self.min_interval    = min_interval
        self.accel_window    = accel_window
        self.player_window   = player_window
        self.strategy_window = strategy_window

    def _load_data(self) -> pd.DataFrame:
        if self.raw_src.lower().endswith(".db"):
            conn = sqlite3.connect(self.raw_src)
            try:
                df = pd.read_sql("SELECT * FROM ruleta_data ORDER BY fecha_hora", conn)
            finally:
                conn.close()
        else:
            df = pd.read_csv(self.raw_src)
        return df

    def clean(self):
        """
        Ejecuta el pipeline de limpieza y enriquecimiento:
        - Convierte y valida fechas y números.
        - Filtra registros inválidos (velocidad, delta_time).
        - Extrae características temporales (cíclicas de hora, minuto y día).
        - Calcula aceleración y estadísticas móviles.
        - Calcula estadísticas móviles de jugadores.
        - Computa ausencias ('runs') para cada categoría incluyendo 'cero'.
        - Calcula streaks de rojos y de victorias.
        - Codifica estrategia previa y sus conteos históricos.
        """
        df = self._load_data()

        # 1) Fecha y número válidos
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], errors='coerce')
        df = (
            df.dropna(subset=['fecha_hora'])
              .sort_values('fecha_hora')
              .reset_index(drop=True)
        )

        df['numero'] = pd.to_numeric(df['numero'], errors='coerce')
        df = df[df['numero'].between(0, 36)]
        df = df.dropna(subset=['numero']).reset_index(drop=True)
        df['numero'] = df['numero'].astype(int)

        # 2) Otras columnas numéricas
        for col in ['velocity', 'ganancia', 'jugadores_presentes', 'fichas']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 3) Filtrar velocity y duplicados
        df = df[df['velocity'] > 0].drop_duplicates().reset_index(drop=True)

        # 4) Delta time
        df['delta_time'] = df['fecha_hora'].diff().dt.total_seconds().fillna(0)
        df = df[(df['delta_time'] >= self.min_interval) & (df['delta_time'] <= 300.0)].reset_index(drop=True)
        max_dt = df['delta_time'].max() or 1.0
        df['delta_time_norm'] = df['delta_time'] / max_dt

        # 5) Características cíclicas de fecha/hora
        df['hour_sin'] = np.sin(2 * np.pi * df['fecha_hora'].dt.hour / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['fecha_hora'].dt.hour / 24)
        df['min_sin']  = np.sin(2 * np.pi * df['fecha_hora'].dt.minute / 60)
        df['min_cos']  = np.cos(2 * np.pi * df['fecha_hora'].dt.minute / 60)
        df['dow']      = df['fecha_hora'].dt.weekday
        df['dow_sin']  = np.sin(2 * np.pi * df['dow'] / 7)
        df['dow_cos']  = np.cos(2 * np.pi * df['dow'] / 7)

        # 6) Aceleración y estadísticas móviles
        df['accel']  = df['velocity'].diff().fillna(0)
        df['accel2'] = df['accel'].diff().fillna(0)
        w = self.accel_window
        df['accel_mean'] = df['accel'].rolling(w).mean().fillna(0)
        df['accel_std']  = df['accel'].rolling(w).std().fillna(0)

        # 7) Estadísticas de jugadores móviles
        wp = self.player_window
        df['players_mean'] = df['jugadores_presentes'].rolling(wp).mean().fillna(0)
        df['players_std']  = df['jugadores_presentes'].rolling(wp).std().fillna(0)
        df['players_skew'] = df['jugadores_presentes'].rolling(wp).apply(pd.Series.skew).fillna(0)

        # 8) Ausencias (runs) por categoría, incluyendo 'cero'
        def in_categories(n: int):
            reds = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
            return {
                'rojo':   n in reds,
                'negro':  n != 0 and n not in reds,
                'par':    n != 0 and n % 2 == 0,
                'impar':  n % 2 == 1,
                '1-18':   1 <= n <= 18,
                '19-36':  19 <= n <= 36,
                'cero':   n == 0
            }

        # Inicializar contadores de runs
        counters = {c: 0 for c in self.CATEGORIES}
        for c in self.CATEGORIES:
            df[f'aus_{c}'] = 0

        for i, n in enumerate(df['numero']):
            flags = in_categories(n)
            for c in self.CATEGORIES:
                counters[c] = 0 if flags[c] else counters[c] + 1
                df.at[i, f'aus_{c}'] = counters[c]

        # 9) Streaks de rojos y victorias
        streak = 0
        df['streak_rojo'] = 0
        for i, n in enumerate(df['numero']):
            if in_categories(n)['rojo']:
                streak += 1
            else:
                streak = 0
            df.at[i, 'streak_rojo'] = streak

        df['streak_win'] = (df['ganancia'] > 0).astype(int)
        df['streak_win'] = (
            df['streak_win']
              .groupby((df['streak_win'] == 0).cumsum())
              .cumsum()
        )

        # 10) Estrategia previa + dummies y conteos históricos
        df['strategy']      = df.get('strategy', '').fillna('none')
        df['strategy_prev'] = df['strategy'].shift(1).fillna('none')
        valid = set(self.CATEGORIES + ['none','other','dqn','ppo','martingala','fibonacci','dalembert'])
        df['strategy_prev'] = df['strategy_prev'].where(df['strategy_prev'].isin(valid), 'other')

        dummies = pd.get_dummies(df['strategy_prev'], prefix='strat')
        df = pd.concat([df, dummies], axis=1)
        for col in dummies.columns:
            df[f'{col}_count'] = dummies[col].rolling(self.strategy_window).sum().fillna(0)

        # 11) Guardar CSV enriquecido
        os.makedirs(os.path.dirname(self.clean_csv) or '.', exist_ok=True)
        df.to_csv(self.clean_csv, index=False)
        print(f"✔️ DataCleaner: {len(df)} registros limpios en '{self.clean_csv}'")
