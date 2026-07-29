# backend/ingestion/excel.py
import pandas as pd

def parse_spreadsheet(file_path: str, filename: str) -> list:
    """Converts CSV and Excel row matrices into highly semantic text chunks"""
    chunks = []
    try:
        # Dynamically determine reading engine based on file type signature
        if filename.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        # Drop entirely empty rows/columns
        df.dropna(how='all', inplace=True)
        
        for idx, row in df.iterrows():
            row_details = " and ".join([f"the {k} is {v}" for k, v in row.to_dict().items() if pd.notna(v)])
            semantic_statement = f"Data record line entry in {filename} at row index {idx} shows that: {row_details}."
            chunks.append({
                "text": semantic_statement,
                "metadata": {
                    "row_index": idx,
                    "type": "spreadsheet"
                }
            })
        return chunks
    except Exception as e:
        print(f"[ERROR] [Spreadsheet Parser Error]: {str(e)}")
        return []