import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import japanize_matplotlib  # 日本語表示を有効化
import os
import random
import time

# --- アプリの基本設定 ---
st.set_page_config(layout="wide")
st.title('棚割り最適化デモ')

# --- ローカルファイルの読み込み ---
DATA_DIR = 'data'
try:
    df_base_initial = pd.read_csv(os.path.join(DATA_DIR, '台.csv'))
    df_shelf_initial = pd.read_csv(os.path.join(DATA_DIR, '棚.csv'))
    df_position_initial = pd.read_csv(os.path.join(DATA_DIR, '棚位置.csv'))
    df_master_initial = pd.read_csv(os.path.join(DATA_DIR, '商品.csv'))
    st.success(f'`{DATA_DIR}/` フォルダからファイルを正常に読み込みました。')
    is_file_loaded = True
except FileNotFoundError as e:
    st.error(f"エラー: {e}. `data` フォルダにCSVファイルがあるか確認してください。")
    is_file_loaded = False


def calculate_layout_score(df_pos, df_master, df_base):
    """現在の棚レイアウトのスコアを計算する"""
    score = 0
    if df_pos.empty: return 0
    df_merged = pd.merge(df_pos, df_master, on='商品コード', how='left')
    for (daiban, tandan), group in df_merged.groupby(['台番号', '棚段番号']):
        sorted_group = group.sort_values('棚位置')
        attributes = sorted_group['飲料属性'].to_list()
        product_codes = sorted_group['商品コード'].to_list()
        for i in range(len(attributes) - 1):
            if attributes[i] == attributes[i+1]:
                score += 1
                if product_codes[i] == product_codes[i+1]:
                    score += 2
        dai_max_width = df_base[df_base['台番号'] == daiban]['フェイス数'].iloc[0]
        current_faces = sorted_group['フェース数'].sum()
        empty_width = dai_max_width - current_faces
        if empty_width > 2:
            score -= (empty_width - 2) * 5
    return score


def optimize_shelf_once(df_pos: pd.DataFrame, df_master: pd.DataFrame, df_base: pd.DataFrame, current_score: float) -> (pd.DataFrame, str, float):
    """スコアが向上する可能性のある入れ替えを1回試行する（単体実行用）"""
    df_copy = df_pos.copy()
    shelf_counts = df_copy.groupby(['台番号', '棚段番号']).size()
    eligible_shelves = shelf_counts[shelf_counts >= 2].index
    if eligible_shelves.empty: return df_copy, "最適化対象の棚がありません。", current_score
    daiban, tandan = random.choice(eligible_shelves)
    shelf_df = df_copy[(df_copy['台番号'] == daiban) & (df_copy['棚段番号'] == tandan)]
    indices_to_swap = shelf_df.sample(2).index
    idx1, idx2 = indices_to_swap[0], indices_to_swap[1]
    pos1 = df_copy.loc[idx1, '棚位置']
    pos2 = df_copy.loc[idx2, '棚位置']
    df_copy.loc[idx1, '棚位置'] = pos2
    df_copy.loc[idx2, '棚位置'] = pos1
    new_score = calculate_layout_score(df_copy, df_master, df_base)
    if new_score > current_score:
        message = f"スコア改善！ ({current_score:.0f} -> {new_score:.0f})\n台-{daiban} 棚段-{tandan} で商品を入れ替えました。"
        return df_copy, message, new_score
    else:
        message = f"スコアが改善しなかったため、変更はありません。({current_score:.0f})"
        return df_pos, message, current_score

# --- ★★★ 新機能①: N回実行用の軽量な最適化関数 ★★★ ---
def optimize_step_for_loop(df_pos: pd.DataFrame, df_master: pd.DataFrame, df_base: pd.DataFrame, current_score: float) -> (pd.DataFrame, float):
    """N回ループ実行用の、メッセージを返さない軽量版"""
    df_copy = df_pos.copy()
    shelf_counts = df_copy.groupby(['台番号', '棚段番号']).size()
    eligible_shelves = shelf_counts[shelf_counts >= 2].index
    if eligible_shelves.empty: return df_pos, current_score
    daiban, tandan = random.choice(eligible_shelves)
    shelf_df = df_copy[(df_copy['台番号'] == daiban) & (df_copy['棚段番号'] == tandan)]
    indices_to_swap = shelf_df.sample(2).index
    idx1, idx2 = indices_to_swap[0], indices_to_swap[1]
    pos1 = df_copy.loc[idx1, '棚位置']
    pos2 = df_copy.loc[idx2, '棚位置']
    df_copy.loc[idx1, '棚位置'] = pos2
    df_copy.loc[idx2, '棚位置'] = pos1
    new_score = calculate_layout_score(df_copy, df_master, df_base)
    if new_score > current_score:
        return df_copy, new_score # 改善した場合のみデータとスコアを返す
    else:
        return df_pos, current_score # 改善しない場合は元のまま


def visualize_store_layout(df_position, df_master, df_base, df_shelf):
    """店全体の棚レイアウトを台ごとに、統一された固定幅で描画する関数"""
    # (可視化関数のコードは変更なしのため省略)
    if 'max_faces_info' not in st.session_state:
        df_base_faces = df_base[['台番号', 'フェイス数']]
        df_shelf_structure = df_shelf[['台番号', '棚段番号']]
        max_faces_info = pd.merge(df_shelf_structure, df_base_faces, on='台番号')
        max_faces_info = max_faces_info.rename(columns={'フェイス数': '最大フェース数'})
        st.session_state['max_faces_info'] = max_faces_info
    df_merged = pd.merge(df_position, df_master, on='商品コード', how='left')
    color_map = { 'お茶': 'green', 'コーヒー': 'black', 'コーラ': 'red', '水': 'blue' }
    df_merged['色'] = df_merged['飲料属性'].map(color_map).fillna('grey')
    dai_groups = df_merged.groupby('台番号')
    for daiban, dai_group in dai_groups:
        st.header(f'台番号: {daiban}')
        dai_max_width = df_base[df_base['台番号'] == daiban]['フェイス数'].iloc[0]
        tandans = sorted(dai_group['棚段番号'].unique())
        num_tandans = len(tandans)
        fig, axes = plt.subplots(nrows=num_tandans, ncols=1, figsize=(12, 1.8 * num_tandans), squeeze=False)
        for i, tandan in enumerate(tandans):
            ax = axes[i][0]
            tandan_group = dai_group[dai_group['棚段番号'] == tandan]
            ax.set_xlim(0, dai_max_width)
            current_pos = 0
            for _, row in tandan_group.sort_values('棚位置').iterrows():
                face_count = row['フェース数']
                color = row['色']
                attribute = row['飲料属性'] if pd.notna(row['飲料属性']) else '不明'
                rect = patches.Rectangle((current_pos, 0), face_count, 1, linewidth=1.5, edgecolor='black', facecolor=color, alpha=0.8)
                ax.add_patch(rect)
                ax.text(current_pos + face_count / 2, 0.5, f"{attribute}\n({face_count}フェイス)", ha='center', va='center', color='white', fontsize=9, weight='bold')
                current_pos += face_count
            empty_width = dai_max_width - current_pos
            if empty_width > 0:
                rect_empty = patches.Rectangle((current_pos, 0), empty_width, 1, facecolor='none', edgecolor='gray', linestyle='--', linewidth=1)
                ax.add_patch(rect_empty)
                ax.text(current_pos + empty_width / 2, 0.5, "空き", ha='center', va='center', color='gray', fontsize=10)
            ax.set_ylim(0, 1)
            ax.set_ylabel(f'棚段 {tandan}', rotation=0, ha='right', va='center', fontsize=12)
            ax.set_xticks(range(0, dai_max_width + 1))
            ax.set_yticks([])
        for i in range(num_tandans - 1):
            axes[i][0].set_xlabel('')
        axes[-1][0].set_xlabel('フェース位置')
        plt.tight_layout(pad=2.0)
        st.pyplot(fig)


# --- メイン処理 ---
if is_file_loaded:
    if 'df_position' not in st.session_state:
        st.session_state.df_base = df_base_initial.copy()
        st.session_state.df_shelf = df_shelf_initial.copy()
        st.session_state.df_position = df_position_initial.copy()
        st.session_state.df_master = df_master_initial.copy()
        st.session_state.current_score = calculate_layout_score(
            st.session_state.df_position, st.session_state.df_master, st.session_state.df_base
        )

    st.markdown('### 棚レイアウト操作')
    
    col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 3])

    # --- ★★★ 新機能②: N回実行のUIを追加 ★★★ ---
    with col1:
        num_iterations = st.number_input("試行回数", min_value=1, max_value=10000, value=500, step=100)
    with col2:
        if st.button(f'{num_iterations}回 最適化を実行', use_container_width=True, type="primary"):
            progress_bar = st.progress(0, text="最適化を実行中...")
            temp_df = st.session_state.df_position.copy()
            current_score = st.session_state.current_score
            initial_score = current_score

            for i in range(num_iterations):
                temp_df, current_score = optimize_step_for_loop(
                    temp_df, st.session_state.df_master, st.session_state.df_base, current_score
                )
                progress_bar.progress((i + 1) / num_iterations, text=f"最適化を実行中... {i+1}/{num_iterations}")
            
            st.session_state.df_position = temp_df
            st.session_state.current_score = current_score
            progress_bar.empty() # プログレスバーを消去
            st.success(f"{num_iterations}回の最適化を実行しました。スコアが {initial_score:.0f} から {current_score:.0f} に改善しました。")

    with col3:
        if st.button('1ステップ最適化', use_container_width=True):
            new_df, message, new_score = optimize_shelf_once(
                st.session_state.df_position, st.session_state.df_master, st.session_state.df_base, st.session_state.current_score
            )
            st.session_state.df_position = new_df
            st.session_state.current_score = new_score
            st.info(message)
    with col4:
        if st.button('リセット', type="secondary", use_container_width=True):
            st.session_state.df_position = df_position_initial.copy()
            if 'max_faces_info' in st.session_state: del st.session_state['max_faces_info']
            st.session_state.current_score = calculate_layout_score(
                st.session_state.df_position, st.session_state.df_master, st.session_state.df_base
            )
            st.success('レイアウトを初期状態にリセットしました。')
    with col5:
        st.metric("現在のレイアウトスコア", f"{st.session_state.current_score:.0f}")

    st.markdown('---') 
    st.markdown('### 現在の棚レイアウト')
    
    visualize_store_layout(
        st.session_state.df_position, 
        st.session_state.df_master,
        st.session_state.df_base,
        st.session_state.df_shelf
    )
