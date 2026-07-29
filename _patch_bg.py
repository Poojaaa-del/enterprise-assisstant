import ast

with open('backend/api/knowledge.py', 'r', encoding='utf-8') as f:
    content = f.read()

START_MARKER = '\n\ndef _bg_process_file('
END_MARKER   = '\n\ndef _log_query_audit('

start = content.find(START_MARKER)
end   = content.find(END_MARKER)

if start == -1 or end == -1:
    print(f"ERROR: markers not found (start={start}, end={end}). Aborting.")
    exit(1)

print(f"Replacing chars {start}..{end} ({end-start} chars old block)")

NEW_FUNC = (
    "\n\n"
    "def _bg_process_file(job_id: str, file_bytes: bytes, filename: str, user_id: int, department: str, permitted_role: str):\n"
    '    """\n'
    "    Background worker: parse -> chunk -> vectorize -> commit SQLite record.\n"
    "\n"
    "    All ChromaDB metadata values are normalised to strings because ChromaDB 0.5.x\n"
    "    enforces str/int/float/bool and filters require explicit string comparisons\n"
    "    (consistent with RetrievalAgent which always uses str(user_id) in where-clauses).\n"
    '    """\n'
    '    print(f"[INFO] [BG Worker] Starting ingestion: \'{filename}\' job={job_id} user={user_id}")\n'
    "    try:\n"
    "        # Step 1: Hash\n"
    "        file_hash = hashlib.sha256(file_bytes).hexdigest()\n"
    '        print(f"[INFO] [BG Worker] SHA-256: {file_hash[:12]}... for \'{filename}\'")\n'
    "\n"
    "        # Step 2: Parse & chunk\n"
    "        try:\n"
    "            parser, _, _, _, _ = _get_agents()\n"
    "            chunks = parser.parse(\n"
    "                file_bytes,\n"
    "                filename,\n"
    "                user_id,\n"
    "                department=department,\n"
    "                permitted_role=permitted_role,\n"
    "            )\n"
    "        except Exception as parse_exc:\n"
    '            msg = f"Document parser raised an exception: {parse_exc}"\n'
    '            print(f"[BACKGROUND WORKER ERROR] {filename} (job={job_id}): {msg}")\n'
    '            _update_job_status(job_id, "failed", detail=msg)\n'
    "            return\n"
    "\n"
    "        if not chunks:\n"
    '            msg = "No text could be extracted from this file."\n'
    '            print(f"[BACKGROUND WORKER ERROR] {filename} (job={job_id}): {msg}")\n'
    '            _update_job_status(job_id, "failed", detail=msg)\n'
    "            return\n"
    "\n"
    '        print(f"[INFO] [BG Worker] Parsed {len(chunks)} chunks from \'{filename}\'")\n'
    "\n"
    "        # Step 3: Normalise metadata so ChromaDB never rejects the add()\n"
    '        # user_id MUST be stored as str to match "$eq": str(user_id) filters.\n'
    "        safe_str_user_id = str(user_id)\n"
    "        for c in chunks:\n"
    '            m = c["metadata"]\n'
    '            m["user_id"] = safe_str_user_id\n'
    '            m["file_hash"] = file_hash\n'
    "            for k, v in list(m.items()):\n"
    "                if v is None:\n"
    '                    m[k] = ""\n'
    "                elif not isinstance(v, (str, int, float, bool)):\n"
    "                    m[k] = str(v)\n"
    "\n"
    "        # Step 4: Purge stale ChromaDB vectors (deduplication)\n"
    "        if collection is not None:\n"
    "            try:\n"
    "                collection.delete(\n"
    "                    where={\n"
    '                        "$and": [\n'
    '                            {"user_id":   {"$eq": safe_str_user_id}},\n'
    '                            {"file_hash": {"$eq": file_hash}},\n'
    "                        ]\n"
    "                    }\n"
    "                )\n"
    '                print(f"[INFO] [BG Worker] Purged existing vectors for hash {file_hash[:8]}")\n'
    "            except Exception as purge_hash_exc:\n"
    '                print(f"[WARNING] [BG Worker] Hash-based purge skipped ({purge_hash_exc}); trying filename purge")\n'
    "                try:\n"
    "                    collection.delete(\n"
    "                        where={\n"
    '                            "$and": [\n'
    '                                {"user_id":  {"$eq": safe_str_user_id}},\n'
    '                                {"filename": {"$eq": filename}},\n'
    "                            ]\n"
    "                        }\n"
    "                    )\n"
    "                except Exception as purge_name_exc:\n"
    '                    print(f"[WARNING] [BG Worker] Filename purge also skipped: {purge_name_exc}")\n'
    "\n"
    "        # Step 5: Add to ChromaDB\n"
    "        if collection is not None:\n"
    '            documents = [c["text"] for c in chunks]\n'
    '            metadatas = [c["metadata"] for c in chunks]\n'
    '            ids = [f"u{user_id}_{file_hash[:10]}_chunk_{i}" for i in range(len(chunks))]\n'
    "            try:\n"
    "                collection.add(documents=documents, metadatas=metadatas, ids=ids)\n"
    '                print(f"[INFO] [BG Worker] Committed {len(chunks)} vectors to ChromaDB for \'{filename}\'")\n'
    "            except Exception as chroma_exc:\n"
    '                msg = f"ChromaDB add() failed: {chroma_exc}"\n'
    '                print(f"[BACKGROUND WORKER ERROR] {filename} (job={job_id}): {msg}")\n'
    '                _update_job_status(job_id, "failed", detail=msg)\n'
    "                return\n"
    "        else:\n"
    '            print(f"[WARNING] [BG Worker] ChromaDB unavailable; skipping vector store for \'{filename}\'")\n'
    "\n"
    "        # Step 6: Commit SQLite knowledge_files record\n"
    "        ext = os.path.splitext(filename.lower())[1]\n"
    "        try:\n"
    "            conn   = sqlite3.connect(DATABASE_PATH)\n"
    "            cursor = conn.cursor()\n"
    "            cursor.execute(\n"
    '                "DELETE FROM knowledge_files WHERE user_id = ? AND file_hash = ?",\n'
    "                (user_id, file_hash),\n"
    "            )\n"
    "            cursor.execute(\n"
    '                """\n'
    "                INSERT INTO knowledge_files\n"
    "                    (user_id, filename, file_type, file_size, chunk_count, status, file_hash)\n"
    "                VALUES (?, ?, ?, ?, ?, 'Indexed', ?)\n"
    '                """,\n'
    "                (\n"
    "                    user_id,\n"
    "                    filename,\n"
    '                    ext.lstrip(".").upper(),\n'
    "                    len(file_bytes),\n"
    "                    len(chunks),\n"
    "                    file_hash,\n"
    "                ),\n"
    "            )\n"
    "            conn.commit()\n"
    "            conn.close()\n"
    '            print(f"[INFO] [BG Worker] SQLite record committed: \'{filename}\' status=Indexed user={user_id}")\n'
    "        except Exception as db_exc:\n"
    '            msg = f"SQLite insert failed: {db_exc}"\n'
    '            print(f"[BACKGROUND WORKER ERROR] {filename} (job={job_id}): {msg}")\n'
    '            _update_job_status(job_id, "failed", detail=msg)\n'
    "            return\n"
    "\n"
    "        # Step 7: Mark ingestion job as completed\n"
    "        _update_job_status(\n"
    '            job_id, "completed",\n'
    "            chunk_count=len(chunks),\n"
    "            file_size=len(file_bytes),\n"
    '            detail=f"Indexed {len(chunks)} chunks (SHA-256: {file_hash[:8]}...)",\n'
    "        )\n"
    '        print(f"[OK] [BG Worker] \'{filename}\' (job={job_id}) -> {len(chunks)} chunks indexed for user {user_id}")\n'
    "\n"
    "    except Exception as exc:\n"
    "        import traceback\n"
    "        tb = traceback.format_exc()\n"
    '        print(f"[BACKGROUND WORKER ERROR] Unhandled exception for \'{filename}\' (job={job_id}): {exc}")\n'
    "        print(tb)\n"
    '        _update_job_status(job_id, "failed", detail=f"Unhandled worker exception: {exc}")\n'
)

new_content = content[:start] + NEW_FUNC + content[end:]

try:
    ast.parse(new_content)
    print("AST parse: OK")
except SyntaxError as se:
    print(f"AST parse FAILED at line {se.lineno}: {se.msg}")
    lines = new_content.splitlines()
    for i in range(max(0, se.lineno - 3), min(len(lines), se.lineno + 2)):
        print(f"  {i+1}: {lines[i]}")
    exit(1)

with open('backend/api/knowledge.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Patch applied successfully.")
