from app.core.config import CHUNK_SIZE,CHUNK_OVERLAP

def split_text(
        text:str,
        chunk_size:int = CHUNK_SIZE,
        chunk_overlap:int = CHUNK_OVERLAP,
)->list[str]:
    text = text.strip()
    if not text:
        return []
    if chunk_size <= 0:
        chunk_size = 500
    if chunk_overlap<0 or chunk_overlap>chunk_size:
        chunk_overlap = chunk_size // 10
    chunks = []          # 装切好的卡片
    start = 0            # 这一刀从哪个字开始
    length = len(text)   # 全文有多少字

    # 3. 一刀一刀往前切，直到切完
    while start < length:

        # 这一刀默认切到 start + chunk_size
        end = start + chunk_size

        # 如果后面还有字，尽量在「段落/句号」处下刀，
        # 别把一句话从中间劈开
        if end < length:
            window = text[start:end]

            # 在窗口里找最靠后的断句点
            cut = max(
                window.rfind("\n\n"),   # 段落
                window.rfind("\n"),     # 换行
                window.rfind("。"),      # 中文句号
                window.rfind(". "),     # 英文句号
                window.rfind("；"),
                window.rfind("; "),
            )

            # 断点太靠前就不用（至少要在窗口 60% 以后），
            # 否则一块变得太短
            if cut > chunk_size * 0.6:
                end = start + cut + 1

        # 取出这一块，去掉首尾空白
        piece = text[start:end].strip()
        if piece:                      # 不是空的才要
            chunks.append(piece)

        # 下一刀从「这一刀结尾往回退 overlap 个字」开始
        # 这样两块之间就有重叠
        start = end - chunk_overlap

        # 防止卡死：如果一点都没往前走，就硬往前挪
        if start < 0:
            start = 0
        if end <= start:
            start = end

    return chunks