# AMC（AIマラソンコーチ）連携実装 引き継ぎ書

## 1. 概要

### 目的
VDOT計算機で入力されたタイム情報を、AMC（AIマラソンコーチ）に自動引き継ぎする機能を実装する。

### 期待される効果
- ユーザーが同じ情報を再入力する手間を削減
- VDOT計算機 → AMC への導線強化（CVR向上）
- AkiRunツール群のエコシステム化

---

## 2. VDOT計算機とは

### 2.1 VDOTについて

**VDOT**は、ランニング指導の世界的権威であるジャック・ダニエルズ博士が考案した「走力指数」です。

- 異なる距離のタイムを統一指標で比較できる（例：5kmとフルマラソンの走力比較）
- VDOTの値が高いほど走力が高い（30〜85の範囲で表現）
- 各VDOTに対応した「適正練習ペース」が定義されている

**例：VDOT 50 のランナー**
| 距離 | 相当タイム |
|------|-----------|
| 5km | 19:57 |
| 10km | 41:21 |
| ハーフ | 1:31:35 |
| フル | 3:10:49 |

### 2.2 VDOT計算機の機能

AkiRunブログで提供しているWebツール（https://akirun.net/vdot-calculator/）

**入力項目：**
- 基準とする距離（5km / 10km / ハーフ / フルマラソン）
- 現在のベストタイム（時間・分・秒）
- 次のフルマラソン目標タイム（時間・分・秒）

**出力内容：**
- 現在のVDOT値
- 目標VDOT値
- 不足スコア（目標との差）
- 目標達成可能性の診断メッセージ
- 推奨練習ペース表（E/M/T/I/Rペース）

### 2.3 VDOT計算機の画面イメージ

```
┌─────────────────────────────────────────────────┐
│         AkiRun式 マラソン実力診断               │
├─────────────────────────────────────────────────┤
│ 基準とするタイムの距離                          │
│ [フルマラソン ▼]                               │
│                                                 │
│ 現在のベストタイム (直近)                       │
│ [4] 時間  [0] 分  [0] 秒                       │
│                                                 │
│ 次のフルマラソン目標タイム                      │
│ [3] 時間  [30] 分  [0] 秒                      │
│                                                 │
│        [ 診断スタート ]                         │
├─────────────────────────────────────────────────┤
│ 結果表示エリア                                  │
│                                                 │
│  現在のVDOT: 42.3   目標VDOT: 48.5   差: +6.2  │
│                                                 │
│  ⚠️ 目標設定が高すぎます...                     │
│                                                 │
│  ▼ 推奨練習ペース                              │
│  E (イージー): 6:23 ～ 5:42 /km                │
│  M (マラソン): 5:16 /km                        │
│  ...                                            │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  [ AIマラソンコーチで練習計画を作成 ]   │   │ ← このリンク
│  │  ✅ 入力したタイム情報がAMCに引き継がれます │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### 2.4 AMCとの関係

| ツール | 役割 | 位置づけ |
|--------|------|---------|
| **VDOT計算機** | 現在の走力を診断、適正ペースを計算 | 入口・診断ツール |
| **AMC** | 12週間の練習計画を自動生成 | メインツール |

**ユーザージャーニー：**
1. VDOT計算機で「自分の走力」と「目標との差」を把握
2. 「じゃあどう練習すればいい？」という疑問が生まれる
3. AMCで具体的な練習計画を作成

この流れをスムーズにするため、VDOT計算機で入力したタイム情報をAMCに引き継ぐ。

---

## 3. 連携フロー

```
┌─────────────────────────────────────────────────────────────┐
│ VDOT計算機 (https://akirun.net/vdot-calculator/)            │
│                                                             │
│  ユーザー入力:                                               │
│   - 現在のベストタイム: 4時間0分0秒（フルマラソン）            │
│   - 目標タイム: 3時間30分0秒                                 │
│                                                             │
│  「診断スタート」クリック → 結果表示                          │
│                                                             │
│  CTAボタン「AIマラソンコーチで練習計画を作成」               │
│   ↓ クリック                                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ AMC LP (https://akirun.net/lp/ai-marathon-coach/)           │
│                                                             │
│  URLパラメータ付きでアクセス:                                │
│  ?best_h=4&best_m=0&best_s=0&target_h=3&target_m=30&target_s=0 │
│                                                             │
│  → フォームに自動入力された状態で表示                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. URLパラメータ仕様

### パラメータ一覧

| パラメータ名 | 型 | 説明 | 値の範囲 |
|-------------|-----|------|---------|
| `best_h` | integer | 現在のベストタイム（時間） | 0-9 |
| `best_m` | integer | 現在のベストタイム（分） | 0-59 |
| `best_s` | integer | 現在のベストタイム（秒） | 0-59 |
| `target_h` | integer | 目標タイム（時間） | 0-9 |
| `target_m` | integer | 目標タイム（分） | 0-59 |
| `target_s` | integer | 目標タイム（秒） | 0-59 |

※すべてフルマラソンのタイムとして扱う

### URL例

```
# サブ3.5を目指す4時間ランナー
https://akirun.net/lp/ai-marathon-coach/?best_h=4&best_m=0&best_s=0&target_h=3&target_m=30&target_s=0

# サブ3を目指す3:15ランナー
https://akirun.net/lp/ai-marathon-coach/?best_h=3&best_m=15&best_s=0&target_h=2&target_m=59&target_s=0

# サブ2:50を目指す2:55ランナー
https://akirun.net/lp/ai-marathon-coach/?best_h=2&best_m=55&best_s=30&target_h=2&target_m=49&target_s=0
```

### 注意事項

1. **タイムはフルマラソン換算済み**
   - VDOT計算機で5km/10km/ハーフを入力した場合も、VDOTからフルマラソン相当タイムに変換してパラメータに設定している

2. **パラメータがない場合**
   - 通常通りの動作（デフォルト値または空欄）でOK
   - パラメータなしでのアクセスも想定すること

3. **不正な値の場合**
   - 範囲外の値が来た場合は無視してデフォルト動作でOK

---

## 5. AMC側で必要な実装

### 5.1 実装内容の概要

ページ読み込み時にURLパラメータを取得し、以下のフォーム項目に初期値としてセットする：

| AMCの入力項目 | 対応パラメータ |
|--------------|---------------|
| 現在のベストタイム（フルマラソン）- 時間 | `best_h` |
| 現在のベストタイム（フルマラソン）- 分 | `best_m` |
| 現在のベストタイム（フルマラソン）- 秒 | `best_s` |
| 目標タイム（フルマラソン）- 時間 | `target_h` |
| 目標タイム（フルマラソン）- 分 | `target_m` |
| 目標タイム（フルマラソン）- 秒 | `target_s` |

### 5.2 実装例（JavaScript）

```javascript
// URLパラメータを取得
function getUrlParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    best_h: params.get('best_h'),
    best_m: params.get('best_m'),
    best_s: params.get('best_s'),
    target_h: params.get('target_h'),
    target_m: params.get('target_m'),
    target_s: params.get('target_s')
  };
}

// フォームに初期値をセット
function applyUrlParamsToForm() {
  const params = getUrlParams();
  
  // ベストタイムをセット
  if (params.best_h !== null) {
    // ※実際のinput要素のIDまたはセレクタに合わせて変更
    setInputValue('現在のベストタイム-時間', parseInt(params.best_h));
    setInputValue('現在のベストタイム-分', parseInt(params.best_m) || 0);
    setInputValue('現在のベストタイム-秒', parseInt(params.best_s) || 0);
  }
  
  // 目標タイムをセット
  if (params.target_h !== null) {
    setInputValue('目標タイム-時間', parseInt(params.target_h));
    setInputValue('目標タイム-分', parseInt(params.target_m) || 0);
    setInputValue('目標タイム-秒', parseInt(params.target_s) || 0);
  }
}

// ページ読み込み時に実行
document.addEventListener('DOMContentLoaded', applyUrlParamsToForm);
```

### 5.3 Reactの場合の実装例

```jsx
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom'; // またはNext.jsのuseSearchParams

function AMCForm() {
  const [searchParams] = useSearchParams();
  
  // 初期値をURLパラメータから取得
  const [bestTime, setBestTime] = useState({
    h: parseInt(searchParams.get('best_h')) || 4,
    m: parseInt(searchParams.get('best_m')) || 0,
    s: parseInt(searchParams.get('best_s')) || 0
  });
  
  const [targetTime, setTargetTime] = useState({
    h: parseInt(searchParams.get('target_h')) || 3,
    m: parseInt(searchParams.get('target_m')) || 30,
    s: parseInt(searchParams.get('target_s')) || 0
  });
  
  // ... フォームのレンダリング
}
```

### 5.4 Streamlitの場合の実装例

```python
import streamlit as st

# URLパラメータを取得
params = st.query_params

# 初期値を設定
default_best_h = int(params.get('best_h', 4))
default_best_m = int(params.get('best_m', 0))
default_best_s = int(params.get('best_s', 0))
default_target_h = int(params.get('target_h', 3))
default_target_m = int(params.get('target_m', 30))
default_target_s = int(params.get('target_s', 0))

# 入力フォーム
col1, col2, col3 = st.columns(3)
with col1:
    best_h = st.number_input('時間', value=default_best_h, min_value=0, max_value=9)
with col2:
    best_m = st.number_input('分', value=default_best_m, min_value=0, max_value=59)
with col3:
    best_s = st.number_input('秒', value=default_best_s, min_value=0, max_value=59)
```

---

## 6. テスト方法

### 6.1 手動テスト

以下のURLでAMCにアクセスし、フォームに値が自動入力されることを確認：

```
# テストケース1: 4:00:00 → 3:30:00
https://akirun.net/lp/ai-marathon-coach/?best_h=4&best_m=0&best_s=0&target_h=3&target_m=30&target_s=0

# テストケース2: 3:28:26 → 3:15:00（秒あり）
https://akirun.net/lp/ai-marathon-coach/?best_h=3&best_m=28&best_s=26&target_h=3&target_m=15&target_s=0

# テストケース3: パラメータなし（通常アクセス）
https://akirun.net/lp/ai-marathon-coach/

# テストケース4: 一部パラメータのみ
https://akirun.net/lp/ai-marathon-coach/?best_h=3&best_m=30
```

### 6.2 確認ポイント

| # | 確認項目 | 期待結果 |
|---|---------|---------|
| 1 | パラメータ付きURLでアクセス | タイム入力欄に値が自動セットされる |
| 2 | パラメータなしでアクセス | デフォルト値で表示される |
| 3 | 不正な値（best_h=99）でアクセス | エラーにならず、無視またはデフォルト値 |
| 4 | 自動入力後に手動で変更 | 正常に変更できる |
| 5 | 自動入力された値で練習計画生成 | 正常に生成される |

---

## 7. 連携元（VDOT計算機）の実装済み内容

### 生成されるリンクURL

```javascript
// VDOT計算機内で生成されるURL
const amcUrl = `https://akirun.net/lp/ai-marathon-coach/?best_h=${best.h}&best_m=${best.m}&best_s=${best.s}&target_h=${target.h}&target_m=${target.m}&target_s=${target.s}`;
```

### フルマラソン換算ロジック

5km/10km/ハーフで入力された場合は、VDOTからフルマラソン相当タイムに変換している：

```javascript
// 例：ハーフ 1:40:20 → VDOT 45 → フルマラソン 3:28:26
if (dist !== 42195) {
  // VDOTからフルマラソンタイムを計算
  bestMarathonSeconds = getMarathonTimeFromVdot(currentVdot);
}
```

---

## 8. 今後の拡張案（参考）

### 8.1 マラソン攻略シミュレーターとの連携

同様のパラメータ設計で、シミュレーターにもタイム情報を引き継ぎ可能：

```
https://akirun.net/marathon-simulator/?target_h=3&target_m=30&target_s=0
```

### 8.2 双方向連携

AMCで生成した練習計画の結果（予測タイム等）を、シミュレーターに渡すことも可能：

```
VDOT計算機 → AMC → シミュレーター
```

---

## 9. 連絡先・質問

実装で不明点があれば、この引き継ぎ書の内容を参照しつつ、必要に応じてあきらに確認してください。

---

**作成日**: 2026年1月19日  
**作成者**: Claude（AkiRunプロジェクト支援）
