# Conjunction Alert Simulator を作った — 軌道力学と衝突回避の縮小版

**ドラフト（技術ブログ用）**

## はじめに

低軌道（LEO）衛星の数は増え続け、宇宙デブリとの接近（Conjunction）は日常の運用課題になっています。本番の衝突回避システムは Space-Track 認証や確率計算（Pc）など高度な要素を含みますが、**TLE + SGP4 + 最接近距離** だけでも「アラートの流れ」は学べます。

本記事では OSS として公開した **Conjunction Alert Simulator（CAS）** の設計と実装の要点をまとめます。

## 何ができるか

1. 自衛星の TLE を入力
2. CelesTrak のデブリカタログと 7 日間・1 分刻みで SGP4 伝播
3. 5 km 以内の接近イベントを距離順に一覧
4. CesiumJS で衛星（青）・デブリ（赤）軌道と TCA を 3D 表示
5. prograde / retrograde / normal の Δv 試算で Before/After の最接近距離を比較

## アーキテクチャ

```
Frontend (CesiumJS)  ←→  FastAPI  ←→  Services
                              ├── tle_fetcher   (CelesTrak + 24h cache)
                              ├── propagator    (SGP4 / TEME)
                              ├── conjunction   (miss distance, risk)
                              └── analysis      (オーケストレーション)
```

- **軌道伝播:** Python `sgp4` ライブラリ（TLE 標準）
- **座標系:** TEME 直交座標（km）で距離計算。Cesium では `ReferenceFrame.INERTIAL` で近似表示
- **API:** FastAPI + Pydantic（OpenAPI 自動生成）

## 接近検出の考え方

各デブリについて、衛星と同じ時刻系列で位置を計算し、ユークリッド距離の最小値を **TCA（Time of Closest Approach）** とします。閾値 5 km 以内をイベントとし、リスクは距離のみで段階付けしています。

| レベル | 条件 |
|--------|------|
| high | < 1 km |
| medium | 1〜3 km |
| low | 3〜5 km |

Phase 1 では Foster 公式などの衝突確率は扱いません。まず「どのデブリがいつ近づくか」を素早く見せることを優先しました。

## 性能: 高度プレフィルタ

デブリは数千件。7 日 × 1 分刻みだと 1 衛星あたり約 10,080 点です。全件フル伝播は 60 秒を超えることがあるため、`analysis` サービスで **衛星の平均高度 ±200 km** のデブリだけに絞るプレフィルタを入れています。LEO 同士の接近検出という用途では妥当な近似です。

## 回避マニューバ試算（Phase 1 の割り切り）

本番では TLE 再生成や精密軌道決定が必要ですが、MVP ではエポック時の速度ベクトルに Δv を加え、**定速度オフセット付き伝播** で Before/After を比較します。燃料最適化ではなく「Δv を入れると miss distance がどう変わるか」の体感用です。

## 使ってみる

```powershell
git clone <your-repo>
cd conjunction-alert-simulator
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000/app/` を開き、ISS サンプルで接近解析を実行してください。

## 今後（Phase 1.5+）

- Space-Track 連携
- 並列伝播・より精密なマニューバモデル
- 複数衛星監視

## まとめ

CAS は Starlink 型の運用フローを学習・ポートフォリオ用に縮小したツールです。SGP4 と REST API と Cesium をつなぐ最小構成ながら、**実際に動く接近アラート** を体験できます。フィードバックは GitHub Issues へお願いします。

**ライセンス:** MIT
