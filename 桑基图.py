import pandas as pd
import plotly.graph_objects as go

file_path = "2025年ESG风险得分Top100数据桑基图-0205.xlsx"
df = pd.read_excel(file_path)

# 算数
df_1 = (
    df.groupby(["纬度", "领域"], as_index=False)["风险指数"]
    .sum()
)
df_2 = (
    df.groupby(["领域", "行业"], as_index=False)["风险指数"]
    .sum()
)

# 列名
labels = pd.concat([
    df_1["纬度"],
    df_1["领域"],
    df_2["行业"]
]).unique().tolist()
label_index = {label: i for i, label in enumerate(labels)}

# 画线
source = (
    df_1["纬度"].map(label_index).tolist() +
    df_2["领域"].map(label_index).tolist()
)
target = (
    df_1["领域"].map(label_index).tolist() +
    df_2["行业"].map(label_index).tolist()
)
value = (
    df_1["风险指数"].tolist() +
    df_2["风险指数"].tolist()
)

# 样式
fig = go.Figure(
    data=[
        go.Sankey(
            arrangement="snap",
            node=dict(
                pad=18,
                thickness=20,
                line=dict(color="black", width=0.4),
                label=labels
            ),
            link=dict(
                source=source,
                target=target,
                value=value
            )
        )
    ]
)

# 导出svg
fig.write_image(
    "final.svg",
    format="svg",
    width=1600,
    height=900,
    scale=1
)