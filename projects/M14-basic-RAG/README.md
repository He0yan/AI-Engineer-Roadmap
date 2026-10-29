1.将pdf或docx文件放入data/raw中
2.运行load_documents.py，加载文档，得到raw.json
3.运行chunk_documents.py，得到按条切分后的法律文本chunks.json
4.运行vector_store.py，将文本块向量化并入库
5.运行rag.py，即可进行基于知识库的问答