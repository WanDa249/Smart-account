"""
图表分析模块，负责绘制统计图表
"""
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager
import pandas as pd
from pathlib import Path


def configure_chart_fonts():
    """为中文环境挑选系统可用字体，避免出现方块字。"""
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "WenQuanYi Zen Hei",
        "Arial Unicode MS",
    ]
    available = {font.name for font in font_manager.fontManager.ttflist}
    picked = [name for name in candidates if name in available]

    # 某些环境下字体已安装但未出现在 Matplotlib 缓存中，尝试按文件路径加载。
    if not picked:
        font_files = [
            Path("C:/Windows/Fonts/msyh.ttc"),
            Path("C:/Windows/Fonts/msyhbd.ttc"),
            Path("C:/Windows/Fonts/simhei.ttf"),
            Path("C:/Windows/Fonts/simsun.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        ]
        for font_file in font_files:
            if not font_file.exists():
                continue
            try:
                font_manager.fontManager.addfont(str(font_file))
                font_name = font_manager.FontProperties(fname=str(font_file)).get_name()
                if font_name:
                    picked.append(font_name)
            except Exception:
                continue

    if not picked:
        picked = ["DejaVu Sans"]

    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = picked + ["DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False


configure_chart_fonts()


class ChartManager:
    def __init__(self, df):
        self.df = df

    def _apply_theme(self):
        plt.style.use("default")
        configure_chart_fonts()
        plt.rcParams.update({
            "figure.facecolor": "#F5EFE6",
            "axes.facecolor": "#EFE5D8",
            "axes.edgecolor": "#CFC0AF",
            "axes.labelcolor": "#4F4A45",
            "xtick.color": "#5D5751",
            "ytick.color": "#5D5751",
            "grid.color": "#D7C9BA",
            "grid.linestyle": "--",
            "grid.alpha": 0.55,
            "axes.titleweight": "bold",
        })

    def _empty_chart(self, title, message):
        self._apply_theme()
        fig, ax = plt.subplots(figsize=(8, 4.8))
        ax.set_title(title, fontsize=14, pad=16)
        ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12, color="#7A746E")
        ax.axis("off")
        fig.tight_layout()
        return fig

    def _build_trend_figure(self, year=None):
        self._apply_theme()
        df = self.df.copy()
        if df.empty:
            return self._empty_chart("收支趋势", "暂无记录，先添加几条账目吧。")

        df["日期"] = pd.to_datetime(df["日期"])
        if year:
            df = df[df["日期"].dt.year == year]
        if df.empty:
            return self._empty_chart("收支趋势", "当前筛选条件下没有可视化数据。")

        df["月度"] = df["日期"].dt.to_period("M")
        monthly_income = df[df["类别"] == "收入"].groupby("月度")["金额"].sum()
        monthly_expense = df[df["类别"] != "收入"].groupby("月度")["金额"].sum().abs()
        period_set = sorted(set(monthly_income.index.tolist()) | set(monthly_expense.index.tolist()))

        if year:
            # 年度图按 1~12 月显示
            months = pd.period_range(start=f"{year}-01", end=f"{year}-12", freq="M")
            income_series = monthly_income.reindex(months, fill_value=0)
            expense_series = monthly_expense.reindex(months, fill_value=0)
            x_plot = list(range(1, len(months) + 1))
            x_labels = [p.strftime("%m") for p in months]
        else:
            # 全部年度按年月排序显示
            months = pd.Index(period_set, name="月份")
            income_series = monthly_income.reindex(months, fill_value=0)
            expense_series = monthly_expense.reindex(months, fill_value=0)
            x_plot = list(range(1, len(months) + 1))
            x_labels = [p.strftime("%Y-%m") for p in months.to_timestamp()]

        balance_series = income_series - expense_series

        fig, ax = plt.subplots(figsize=(9.2, 5.1))
        ax.plot(x_plot, income_series.values, marker='o', linewidth=2.4, color="#7F9B82", label='收入')
        ax.plot(x_plot, expense_series.values, marker='o', linewidth=2.4, color="#B7877C", label='支出')
        ax.fill_between(x_plot, balance_series.values, 0, where=(balance_series.values >= 0), color="#C9D4C1", alpha=0.36, label='结余区间')
        ax.fill_between(x_plot, balance_series.values, 0, where=(balance_series.values < 0), color="#E1CFC8", alpha=0.45, label='亏损区间')

        for pos, month in enumerate(months, start=1):
            income = income_series.loc[month]
            expense = expense_series.loc[month]
            if income > 0:
                ax.annotate(f"{income:.0f}", (pos, income), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9, color="#5E765F")
            if expense > 0:
                ax.annotate(f"{expense:.0f}", (pos, expense), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=9, color="#8C645A")

        ax.set_title(f"{year if year else '全部'}年度收支趋势", fontsize=14, pad=14)
        ax.set_xlabel("月份", fontsize=11)
        ax.set_ylabel("金额", fontsize=11)
        ax.set_xticks(x_plot)
        ax.set_xticklabels(x_labels, rotation=40, ha='right')
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.axhline(0, color="#AFA092", linewidth=1.1, alpha=0.65)
        ax.grid(True)
        ax.legend(loc="upper left", frameon=False)
        fig.tight_layout()
        return fig

    def _build_category_pie_figure(self):
        self._apply_theme()
        df = self.df.copy()
        if df.empty:
            return self._empty_chart("分类饼图", "暂无记录，先添加几条账目吧。")

        df_income = df[df["类别"] == "收入"].copy()
        if not df_income.empty:
            df_income["备注"] = df_income["备注"].fillna("").astype(str).str.strip()
            df_income.loc[df_income["备注"] == "", "备注"] = "未备注"
        income_by_category = df_income.groupby("备注")["金额"].sum()

        df_expense = df[df["类别"] != "收入"].copy()
        expense_by_category = df_expense.groupby("类别")["金额"].sum().abs()

        if income_by_category.empty and expense_by_category.empty:
            return self._empty_chart("分类饼图", "当前暂无可分组的收入或支出数据。")

        fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.2), subplot_kw=dict(aspect="equal"))
        fig.suptitle("收支分类分布", fontsize=15, y=0.98)

        income_colors = ["#8AA78D", "#A0B89D", "#BAC9B1", "#D1DDC9", "#9CB1A2"]
        expense_colors = ["#BF8F86", "#CEA29A", "#DDB7AF", "#E8CCC5", "#B9837A", "#CBA49D"]

        def smart_pct(pct):
            return f"{pct:.1f}%" if pct >= 3 else ""

        if income_by_category.empty:
            axes[0].text(0.5, 0.5, "暂无收入数据", ha="center", va="center", fontsize=12, color="#7A746E")
            axes[0].axis("off")
        else:
            wedges, _, _ = axes[0].pie(
                income_by_category.values,
                labels=income_by_category.index,
                colors=income_colors[:len(income_by_category)],
                startangle=110,
                autopct=smart_pct,
                pctdistance=0.78,
                wedgeprops={"linewidth": 1, "edgecolor": "#F5EFE6"},
                textprops={"fontsize": 10, "color": "#4F4A45"},
            )
            axes[0].add_artist(plt.Circle((0, 0), 0.46, color="#F5EFE6"))
            axes[0].set_title("收入构成", fontsize=12)
            axes[0].legend(wedges, income_by_category.index, loc="lower center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False, fontsize=9)

        if expense_by_category.empty:
            axes[1].text(0.5, 0.5, "暂无支出数据", ha="center", va="center", fontsize=12, color="#7A746E")
            axes[1].axis("off")
        else:
            wedges, _, _ = axes[1].pie(
                expense_by_category.values,
                labels=expense_by_category.index,
                colors=expense_colors[:len(expense_by_category)],
                startangle=105,
                autopct=smart_pct,
                pctdistance=0.78,
                wedgeprops={"linewidth": 1, "edgecolor": "#F5EFE6"},
                textprops={"fontsize": 10, "color": "#4F4A45"},
            )
            axes[1].add_artist(plt.Circle((0, 0), 0.46, color="#F5EFE6"))
            axes[1].set_title("支出构成", fontsize=12)
            axes[1].legend(wedges, expense_by_category.index, loc="lower center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False, fontsize=9)

        fig.tight_layout(rect=[0, 0.02, 1, 0.95])
        return fig

    def show_trend(self, year=None):
        fig = self._build_trend_figure(year)
        plt.show()

    def show_category_pie(self):
        fig = self._build_category_pie_figure()
        plt.show()

    def save_trend(self, file_path, year=None):
        fig = self._build_trend_figure(year)
        fig.savefig(file_path, dpi=180, bbox_inches="tight")
        plt.close(fig)

    def save_category_pie(self, file_path):
        fig = self._build_category_pie_figure()
        fig.savefig(file_path, dpi=180, bbox_inches="tight")
        plt.close(fig)




