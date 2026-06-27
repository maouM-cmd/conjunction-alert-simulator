# Conjunction Alert Simulator を作った — 軌道力学と衝突回避の縮小版

**公開リポ:** https://github.com/maouM-cmd/conjunction-alert-simulator

## はじめに

低軌道（LEO）衛星の数は増え続け、宇宙デブリとの接近（Conjunction）は日常の運用課題になっています。本番の衝突回避システムは Space-Track 認証や確率計算（Pc）など高度な要素を含みますが、**TLE + SGP4 + 最接近距離** だけでも「アラートの流れ」は学べます。

本記事では OSS として公開した **Conjunction Alert Simulator（CAS）** の設計と実装の要点をまとめます。

![Demo](demo.gif)

## 何ができるか

1. 自衛星の TLE を入力（**デモ TLE 読込** ボタン付き）
2. CelesTrak のデブリカタログと 7 日間・1 分刻みで SGP4 伝播
3. 閾値以内の接近イベントを距離順に一覧
4. CesiumJS で衛星（青）・デブリ（赤）軌道と TCA を 3D 表示
5. prograde / retrograde / normal の Δv 試算で Before/After の最接近距離を比較

## アーキテクチャ

```
Frontend (CesiumJS)  ←→  FastAPI  ←→  Services
                              ├── tle_fetcher   (CelesTrak + 24h cache)
                              ├── propagator    (SGP4 / TEME)
                              ├── conjunction   (miss distance, risk)
                              └── analysis      (高度プレフィルタ ±200 km)
```

- **軌道伝播:** Python `sgp4` ライブラリ（TLE 標準）
- **座標系:** TEME 直交座標（km）で距離計算。Cesium では `ReferenceFrame.INERTIAL` で近似表示
- **API:** FastAPI + Pydantic（OpenAPI 自動生成）

## 接近検出の考え方

各デブリについて、衛星と同じ時刻系列で位置を計算し、ユークリッド距離の最小値を **TCA（Time of Closest Approach）** とします。

| レベル | 条件 |
|--------|------|
| high | < 1 km |
| medium | 1〜3 km |
| low | 3〜5 km |

Phase 1 では Foster 公式などの衝突確率 Pc は扱いません。まず「どのデブリがいつ近づくか」を素早く見せることを優先しました。

## デモ用 TLE の自動生成

ISS サンプルでは 5 km 閾値で接近 0 件になりがちです。`backend/cli/find_demo_pair.py` でカタログから最接近デブリを探索し、`samples/demo-satellite.tle` を生成しています（例: ISS vs COSMOS 2251 DEB、約 30 km）。

## 使ってみる

```powershell
git clone https://github.com/maouM-cmd/conjunction-alert-simulator.git
cd conjunction-alert-simulator
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000/app/` を開き、**デモ TLE 読込** → **接近解析**（閾値 50 km）を試してください。

## 今後（Phase 3）

- 複数衛星監視
- CDM インポート

## まとめ

CAS は Starlink 型の運用フローを学習・ポートフォリオ用に縮小したツールです。SGP4 と REST API と Cesium をつなぐ最小構成ながら、**実際に動く接近アラート** を体験できます。

**ライセンス:** MIT
