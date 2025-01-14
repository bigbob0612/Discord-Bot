import json

def load_json(file_path):
    """Locad and parse a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"파일 {file_path}을(를) 찾을 수 없습니다.")
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 디코딩 오류: {e}")