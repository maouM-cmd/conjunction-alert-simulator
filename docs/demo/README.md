# デモ手順

Conjunction Alert Simulator（CAS）のデモ用スクリーンショット・GIF 作成手順です。

## 前提

```powershell
cd C:\Users\admin\OneDrive\ドキュメント\conjunction-alert-simulator
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

ブラウザで `http://127.0.0.1:8000/app/` を開く。

## 推奨キャプチャシーケンス

### 1. 初期画面

- ISS サンプル TLE が入力済みの状態
- 左パネル + 右 Cesium 地球
- ファイル名例: `01-initial.png`

### 2. 接近解析結果

1. **接近解析** をクリック
2. 数十秒待ち、接近イベント一覧が表示される
3. リスク色（high=赤 / medium=橙 / low=緑）が付いたリストをキャプチャ
- ファイル名例: `02-conjunctions.png`

### 3. 3D 軌道 + TCA

1. 一覧から1件クリック
2. 青（衛星）・赤（デブリ）軌道と黄色 TCA マーカーが表示
3. タイムラインを TCA 付近に合わせる
- ファイル名例: `03-orbit-tca.png`

### 4. 回避マニューバ試算

1. 方向（prograde 等）と Δv（例: 0.1 m/s）を設定
2. **試算実行** → Before/After の最接近距離をキャプチャ
- ファイル名例: `04-maneuver.png`

## GIF 作成（任意）

- Windows: Xbox Game Bar（Win+G）または OBS で 30〜60 秒録画
- 流れ: 解析 → イベント選択 → 3D 表示 → マニューバ試算
- `docs/demo/demo.gif` として保存し README にリンク

## API デモ（curl）

```powershell
curl http://127.0.0.1:8000/health
```

```powershell
venv\Scripts\python -c "
import httpx, pathlib
tle = pathlib.Path('samples/iss.tle').read_text(encoding='utf-8')
r = httpx.post('http://127.0.0.1:8000/api/v1/orbit', json={'tle': tle}, timeout=30)
print(r.status_code, r.json()['name'], len(r.json()['points']))
"
```

## 注意

- 初回は CelesTrak からデブリカタログを取得するためネットワークが必要
- キャッシュは `data/cache/` に 24 時間保持
