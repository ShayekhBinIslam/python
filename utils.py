def extract_substring(text, start_tag, end_tag):
    start_position = text.lower().find(start_tag.lower())
    end_position = text.lower().find(end_tag.lower())

    if start_position == -1 or end_position == -1:
        return None

    return text[start_position + len(start_tag):end_position].strip()