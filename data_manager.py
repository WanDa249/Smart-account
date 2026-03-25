"""
数据管理模块，负责收支记录的增删查改和统计分析
"""
import pandas as pd
import csv
import shutil
from pathlib import Path

DEFAULT_BOOK = "records.csv"
PROJECT_DIR = Path(__file__).parent
BOOKS_DIR = PROJECT_DIR / "books"


def get_data_dir():
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    return str(BOOKS_DIR)


def ensure_default_book(data_path):
    data_dir = Path(data_path)
    data_dir.mkdir(parents=True, exist_ok=True)
    default_file = data_dir / DEFAULT_BOOK
    legacy_file = PROJECT_DIR / DEFAULT_BOOK

    if not default_file.exists() and legacy_file.exists():
        shutil.copyfile(str(legacy_file), str(default_file))

    if not default_file.exists():
        with open(default_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["日期", "类别", "金额", "备注"])

class BookManager:
    def __init__(self, data_path=None):
        self.data_path = Path(data_path) if data_path else Path(get_data_dir())
        ensure_default_book(self.data_path)
        self.books = self.list_books()
        self.current_book = self.books[0] if self.books else DEFAULT_BOOK

    def list_books(self):
        return sorted([f.name for f in self.data_path.iterdir() if f.is_file() and f.suffix == ".csv"])

    def new_book(self, name):
        file = self.data_path / f"{name}.csv"
        if not file.exists():
            with open(file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["日期", "类别", "金额", "备注"])
        book_name = f"{name}.csv"
        if book_name not in self.books:
            self.books.append(book_name)
        self.current_book = book_name

    def switch_book(self, name):
        book_name = f"{name}.csv"
        if book_name in self.books:
            self.current_book = book_name

    def delete_book(self, name):
        file = self.data_path / f"{name}.csv"
        book_name = f"{name}.csv"
        if file.exists():
            file.unlink()
            if book_name in self.books:
                self.books.remove(book_name)
            self.current_book = self.books[0] if self.books else DEFAULT_BOOK

class DataManager:
    def export_pdf(self, pdf_file):
        from matplotlib import pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        from chart import ChartManager, configure_chart_fonts

        configure_chart_fonts()
        df = self.df.copy()
        chart_mgr = ChartManager(df)

        income_total = df[df["类别"] == "收入"]["金额"].sum() if not df.empty else 0.0
        expense_total = abs(df[df["类别"] != "收入"]["金额"].sum()) if not df.empty else 0.0
        balance_total = income_total - expense_total
        top_categories = df[df["类别"] != "收入"].groupby("类别")["金额"].sum().abs().sort_values(ascending=False).head(6)

        with PdfPages(pdf_file) as pdf:
            # 首页：摘要统计
            fig, ax = plt.subplots(figsize=(8.5, 6.2))
            ax.axis("off")
            fig.patch.set_facecolor("#F5EFE6")
            ax.set_facecolor("#F5EFE6")

            ax.text(0.05, 0.93, "账本导出摘要", fontsize=19, fontweight="bold", color="#4F4A45")
            ax.text(0.05, 0.86, f"记录总数：{len(df)} 条", fontsize=12, color="#5D5751")
            ax.text(0.05, 0.80, f"总收入：{income_total:.2f}", fontsize=12, color="#5E765F")
            ax.text(0.05, 0.74, f"总支出：{expense_total:.2f}", fontsize=12, color="#8C645A")
            ax.text(0.05, 0.68, f"结余：{balance_total:.2f}", fontsize=12, color="#4F4A45")

            table_data = [[cat, f"{amt:.2f}"] for cat, amt in top_categories.items()]
            if not table_data:
                table_data = [["暂无支出分类数据", "0.00"]]
            table = ax.table(cellText=table_data, colLabels=["支出分类", "金额"], loc="center", bbox=[0.05, 0.1, 0.9, 0.46])
            table.auto_set_font_size(False)
            table.set_fontsize(11)
            table.scale(1, 1.3)
            pdf.savefig(fig)
            plt.close(fig)

            # 第二页：新版趋势图
            trend_fig = chart_mgr._build_trend_figure()
            pdf.savefig(trend_fig)
            plt.close(trend_fig)

            # 第三页：新版分类饼图
            pie_fig = chart_mgr._build_category_pie_figure()
            pdf.savefig(pie_fig)
            plt.close(pie_fig)

        return pdf_file


    def __init__(self, data_path=None, book_file=None):
        self.data_path = Path(data_path) if data_path else Path(get_data_dir())
        ensure_default_book(self.data_path)
        self.book_file = book_file or DEFAULT_BOOK
        self.file = self.data_path / self.book_file
        if not self.file.exists():
            with open(self.file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["日期", "类别", "金额", "备注"])
        self.load_dataframe()

    def load_dataframe(self):
        records = []
        with open(self.file, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if not row or all(str(cell).strip() == "" for cell in row):
                    continue
                if len(row) >= 4:
                    date, category, amount = row[0], row[1], row[2]
                    remark = ",".join(row[3:]).strip()
                elif len(row) == 3:
                    date, category, amount = row
                    remark = ""
                else:
                    continue
                records.append({"日期": date, "类别": category, "金额": amount, "备注": remark})
        self.df = pd.DataFrame(records, columns=["日期", "类别", "金额", "备注"])
        self.df["金额"] = pd.to_numeric(self.df["金额"], errors="coerce").fillna(0.0)

    def add_record(self, date, category, amount, remark):
        new_row = {"日期": date, "类别": category, "金额": amount, "备注": remark}
        self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
        self.df.to_csv(self.file, index=False)

    def get_records(self, date_range=None, category=None, amount_range=None, remark_keyword=None):
        df = self.df.copy()
        if date_range:
            df = df[(df["日期"] >= date_range[0]) & (df["日期"] <= date_range[1])]
        if category:
            df = df[df["类别"] == category]
        if amount_range:
            df = df[(df["金额"] >= amount_range[0]) & (df["金额"] <= amount_range[1])]
        if remark_keyword:
            df = df[df["备注"].str.contains(remark_keyword, na=False)]
        return df

    def edit_record(self, idx, date=None, category=None, amount=None, remark=None):
        if idx < 0 or idx >= len(self.df):
            raise IndexError("记录索引超出范围")
        if date:
            self.df.at[idx, "日期"] = date
        if category:
            self.df.at[idx, "类别"] = category
        if amount:
            self.df.at[idx, "金额"] = amount
        if remark:
            self.df.at[idx, "备注"] = remark


    # 删除指定索引的记录
    def delete_record(self, idx):
        """删除指定索引的收支记录"""
        if idx < 0 or idx >= len(self.df):
            raise IndexError("记录索引超出范围")
        self.df = self.df.drop(idx).reset_index(drop=True)
        self.df.to_csv(self.file, index=False)

    # 批量删除记录
    def batch_delete(self, idx_list):
        """批量删除收支记录"""
        self.df = self.df.drop(idx_list).reset_index(drop=True)
        self.df.to_csv(self.file, index=False)

    # 导入CSV数据
    def import_csv(self, import_file):
        """导入CSV文件到当前账本"""
        import_df = pd.read_csv(import_file)
        self.df = pd.concat([self.df, import_df], ignore_index=True)
        self.df.to_csv(self.file, index=False)

    # 导出CSV数据
    def export_csv(self, export_file):
        """导出当前账本为CSV文件"""
        self.df.to_csv(export_file, index=False)

    # 月度收支统计
    def monthly_stats(self, year=None):
        """按月统计收支总额"""
        df = self.df.copy()
        df["日期"] = pd.to_datetime(df["日期"])
        if year:
            df = df[df["日期"].dt.year == year]
        stats = df.groupby(df["日期"].dt.month)["金额"].agg(["sum"])
        return stats

    # 年度收支统计
    def yearly_stats(self):
        """按年统计收支总额"""
        df = self.df.copy()
        df["日期"] = pd.to_datetime(df["日期"])
        stats = df.groupby(df["日期"].dt.year)["金额"].agg(["sum"])
        return stats

    # 按类别统计收支
    def category_stats(self):
        """按类别统计收支总额"""
        stats = self.df.groupby("类别")["金额"].agg(["sum"]).sort_values("sum", ascending=False)
        return stats
