import ast

with open('backend/agents/document_parser.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines 48-55 (0-indexed) are the old meta dict block
# 48: '        if chunk_text:\n'
# 49: '            meta = {\n'
# 50: '                **base_metadata,\n'
# 51: '                "filename":   filename,\n'
# 52: '                "user_id":    user_id,\n'                  <- BUG: int, not str
# 53: '                "department": str(department),    # RBAC department scoping\n'
# 54: '                "permitted_role": str(permitted_role),\n'
# 55: '            }\n'
# 56: '            chunks.append({"text": chunk_text, "metadata": meta})\n'

replacement = [
    '        if chunk_text:\n',
    '            meta = {\n',
    '                **base_metadata,\n',
    '                "filename":       filename,\n',
    '                "user_id":        str(user_id),       # str for ChromaDB filter compat\n',
    '                "department":     str(department),\n',
    '                "permitted_role": str(permitted_role),\n',
    '            }\n',
    '            chunks.append({"text": chunk_text, "metadata": meta})\n',
]

new_lines = lines[:48] + replacement + lines[57:]

src = ''.join(new_lines)
try:
    ast.parse(src)
    print('AST parse: OK')
except SyntaxError as se:
    print(f'AST FAILED at line {se.lineno}: {se.msg}')
    exit(1)

with open('backend/agents/document_parser.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('document_parser.py patched successfully.')
