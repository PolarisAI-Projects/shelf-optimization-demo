import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# --- アプリの基本設定 ---
st.set_page_config(layout="wide")  # 画面を広く使う設定
st.title("棚割り最適化デモ")
st.markdown("### Step 1: 棚の状態を可視化する")

# --- サイドバーにファイルアップローダーを設置 ---
st.sidebar.header("CSVファイルをアップロード")
uploaded_base = st.sidebar.file_uploader("1. 台.csv", type="csv")
uploaded_shelf = st.sidebar.file_uploader("2. 棚.csv", type="csv")
uploaded_position = st.sidebar.file_uploader("3. 棚位置.csv", type="csv")
uploaded_master = st.sidebar.file_uploader("4. 商品.csv", type="csv")


def visualize_shelves(df_position, df_master):
    """
    棚のレイアウトを可視化する関数
    """
    # 商品マスタをマージして、各商品に飲料属性を付与
    df = pd.merge(df_position, df_master, on="商品コード", how="left")

    # 飲料属性ごとに色を定義
    color_map = {"お茶": "green", "コーラ": "red", "水": "blue"}
    # 属性がない場合はグレー
    df["色"] = df["飲料属性"].map(color_map).fillna("grey")

    # 台番号と棚段番号でグループ化
    grouped = df.groupby(["台番号", "棚段番号"])

    # 台ごとにグラフを描画
    for (daiban, tandan), group in grouped:
        # 新しい台番号のときにヘッダーを表示
        if (
            "current_daiban" not in st.session_state
            or st.session_state.current_daiban != daiban
        ):
            st.header(f"台番号: {daiban}")
            st.session_state.current_daiban = daiban

        st.subheader(f"棚段: {tandan}")

        fig, ax = plt.subplots(figsize=(12, 1.5))  # 棚段ごとにグラフを作成

        # 描画する棚の初期位置
        current_pos = 0

        # 棚段内の商品を一つずつ描画
        for _, row in group.sort_values("棚位置").iterrows():
            face_count = row["フェース数"]
            color = row["色"]
            product_code = str(row["商品コード"])
            attribute = row["飲料属性"] if pd.notna(row["飲料属性"]) else "不明"

            # 商品（フェース）を表す四角形を描画
            rect = patches.Rectangle(
                (current_pos, 0),
                face_count,
                1,
                linewidth=1,
                edgecolor="black",
                facecolor=color,
                alpha=0.7,
            )
            ax.add_patch(rect)

            # 四角形の中にテキストを表示
            ax.text(
                current_pos + face_count / 2,
                0.5,
                f"{attribute}\n({face_count}フェイス)",
                ha="center",
                va="center",
                color="white",
                fontsize=8,
                weight="bold",
            )

            # 次の商品の描画位置を更新
            current_pos += face_count

        # グラフの見た目を調整
        ax.set_xlim(0, current_pos)
        ax.set_ylim(0, 1)
        ax.set_yticks([])  # y軸の目盛りは不要
        ax.set_xlabel("フェース位置")
        plt.tight_layout()

        # Streamlitにグラフを表示
        st.pyplot(fig)


# --- メイン処理 ---
# すべてのファイルがアップロードされたら処理を実行
if uploaded_base and uploaded_shelf and uploaded_position and uploaded_master:
    try:
        # CSVをDataFrameに読み込み
        df_base = pd.read_csv(uploaded_base)
        df_shelf = pd.read_csv(uploaded_shelf)
        df_position = pd.read_csv(uploaded_position)
        df_master = pd.read_csv(uploaded_master)

        st.success("すべてのファイルが正常に読み込まれました。")

        # 可視化関数を呼び出し
        if "current_daiban" in st.session_state:
            del st.session_state.current_daiban  # 描画前にリセット
        visualize_shelves(df_position, df_master)

    except Exception as e:
        st.error(f"ファイルの読み込みまたは処理中にエラーが発生しました: {e}")
else:
    st.info("サイドバーから4種類のCSVファイルをアップロードしてください。")
