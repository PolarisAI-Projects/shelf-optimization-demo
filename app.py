import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import japanize_matplotlib  # 日本語表示を有効化
import os
import random

st.set_page_config(layout="wide")
st.title('棚割り最適化デモ')

# --- ローカルファイルの読み込み ---
DATA_DIR = 'data'
try:
    df_base_initial = pd.read_csv(os.path.join(DATA_DIR, '台.csv')) # 新しい 台.csv を読み込み
    df_shelf_initial = pd.read_csv(os.path.join(DATA_DIR, '棚.csv'))
    df_position_initial = pd.read_csv(os.path.join(DATA_DIR, '棚位置.csv'))
    df_master_initial = pd.read_csv(os.path.join(DATA_DIR, '商品.csv'))
    st.success(f'`{DATA_DIR}/` フォルダからファイルを正常に読み込みました。')
    is_file_loaded = True
except FileNotFoundError as e:
    st.error(f"エラー: {e}. `data` フォルダにCSVファイルがあるか確認してください。")
    is_file_loaded = False


def swap_random_products_on_shelf(df_pos: pd.DataFrame) -> (pd.DataFrame, str):
    """
    同じ棚段内で、ランダムに2つの商品の「棚位置」を入れ替える
    """
    df_copy = df_pos.copy()
    shelf_counts = df_copy.groupby(['台番号', '棚段番号']).size()
    eligible_shelves = shelf_counts[shelf_counts >= 2].index
    if eligible_shelves.empty:
        return df_copy, "入れ替え可能な棚がありません。"
    daiban, tandan = random.choice(eligible_shelves)
    shelf_df = df_copy[(df_copy['台番号'] == daiban) & (df_copy['棚段番号'] == tandan)]
    indices_to_swap = shelf_df.sample(2).index
    idx1, idx2 = indices_to_swap[0], indices_to_swap[1]
    pos1 = df_copy.loc[idx1, '棚位置']
    pos2 = df_copy.loc[idx2, '棚位置']
    df_copy.loc[idx1, '棚位置'] = pos2
    df_copy.loc[idx2, '棚位置'] = pos1
    product1_code = df_copy.loc[idx1, '商品コード']
    product2_code = df_copy.loc[idx2, '商品コード']
    message = f"台-{daiban} 棚段-{tandan} で、商品コード {product1_code} と {product2_code} の位置を入れ替えました。"
    return df_copy, message


def visualize_store_layout(df_position, df_master, df_base, df_shelf):
    """
    店全体の棚レイアウトを台ごとに、統一された固定幅で描画する関数
    """
    if 'max_faces_info' not in st.session_state:
        df_base_faces = df_base[['台番号', 'フェイス数']]
        df_shelf_structure = df_shelf[['台番号', '棚段番号']]
        max_faces_info = pd.merge(df_shelf_structure, df_base_faces, on='台番号')
        max_faces_info = max_faces_info.rename(columns={'フェイス数': '最大フェース数'})
        st.session_state['max_faces_info'] = max_faces_info
        
        with st.expander("各棚段の最大フェース数（キャパシティ）- 台.csvより算出"):
            st.dataframe(max_faces_info)

    df_merged = pd.merge(df_position, df_master, on='商品コード', how='left')
    
    color_map = {
        'お茶': 'green', 'コーヒー': 'black', 'コーラ': 'red', '水': 'blue'
    }
    df_merged['色'] = df_merged['飲料属性'].map(color_map).fillna('grey')

    dai_groups = df_merged.groupby('台番号')

    for daiban, dai_group in dai_groups:
        st.header(f'台番号: {daiban}')

        dai_max_width = df_base[df_base['台番号'] == daiban]['フェイス数'].iloc[0]
        
        tandans = sorted(dai_group['棚段番号'].unique())
        num_tandans = len(tandans)

        fig, axes = plt.subplots(
            nrows=num_tandans, ncols=1, 
            figsize=(12, 1.8 * num_tandans), squeeze=False
        )
        
        for i, tandan in enumerate(tandans):
            ax = axes[i][0]
            tandan_group = dai_group[dai_group['棚段番号'] == tandan]
            
            ax.set_xlim(0, dai_max_width)

            current_pos = 0
            for _, row in tandan_group.sort_values('棚位置').iterrows():
                face_count = row['フェース数']
                color = row['色']
                attribute = row['飲料属性'] if pd.notna(row['飲料属性']) else '不明'
                
                rect = patches.Rectangle(
                    (current_pos, 0), face_count, 1, 
                    linewidth=1.5, edgecolor='black', facecolor=color, alpha=0.8
                )
                ax.add_patch(rect)
                
                ax.text(
                    current_pos + face_count / 2, 0.5,
                    f"{attribute}\n({face_count}フェイス)",
                    ha='center', va='center', color='white', fontsize=9, weight='bold'
                )
                current_pos += face_count

            empty_width = dai_max_width - current_pos
            if empty_width > 0:
                rect_empty = patches.Rectangle(
                    (current_pos, 0), empty_width, 1,
                    facecolor='none', edgecolor='gray', linestyle='--', linewidth=1
                )
                ax.add_patch(rect_empty)
                ax.text(
                    current_pos + empty_width / 2, 0.5, "空き",
                    ha='center', va='center', color='gray', fontsize=10
                )
                
            ax.set_ylim(0, 1)
            ax.set_ylabel(f'棚段 {tandan}', rotation=0, ha='right', va='center', fontsize=12)
            ax.set_xticks(range(0, dai_max_width + 1))
            ax.set_yticks([])

        for i in range(num_tandans - 1):
            axes[i][0].set_xlabel('')
        axes[-1][0].set_xlabel('フェース位置')

        plt.tight_layout(pad=2.0)
        st.pyplot(fig)


if is_file_loaded:
    # session_stateが初期化されていなければ、読み込んだデータで初期化
    if 'df_position' not in st.session_state:
        st.session_state.df_base = df_base_initial.copy()
        st.session_state.df_shelf = df_shelf_initial.copy()
        st.session_state.df_position = df_position_initial.copy()
        st.session_state.df_master = df_master_initial.copy()

    st.markdown('### 棚レイアウト操作')
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button('商品をランダムに入れ替え', use_container_width=True):
            new_df, message = swap_random_products_on_shelf(st.session_state.df_position)
            st.session_state.df_position = new_df
            st.info(message)
    with col2:
        if st.button('レイアウトをリセット', type="secondary", use_container_width=True):
            # session_stateを初期データで上書き
            st.session_state.df_position = df_position_initial.copy()
            # キャパシティ情報もリセットして再計算させる
            if 'max_faces_info' in st.session_state:
                del st.session_state['max_faces_info']
            st.success('レイアウトを初期状態にリセットしました。')

    st.markdown('---') 
    st.markdown('### 現在の棚レイアウト')
    
    visualize_store_layout(
        st.session_state.df_position, 
        st.session_state.df_master,
        st.session_state.df_base,
        st.session_state.df_shelf
    )
