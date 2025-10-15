import jsonpath
import re


class ExtractUtil:
    extract_data = {}

    @classmethod
    def extract_values(cls, response, extract_rules):
        for key, rule in extract_rules.items():
            if rule.startswith('jsonpath:'):
                expr = rule.replace('jsonpath:', '').strip()
                value = jsonpath.jsonpath(response.json(), expr)
                if value:
                    cls.extract_data[key] = value[0]
            elif rule.startswith('header:'):
                header_name = rule.replace('header:', '').strip()
                cls.extract_data[key] = response.headers.get(header_name)

    @classmethod
    def replace_dynamic_values(cls, data):
        if isinstance(data, dict):
            return {k: cls.replace_dynamic_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.replace_dynamic_values(item) for item in data]
        elif isinstance(data, str):
            pattern = r'\$\{(.*?)\}'
            matches = re.findall(pattern, data)
            for var in matches:
                if var in cls.extract_data:
                    data = data.replace(f'${{{var}}}', str(cls.extract_data[var]))
            return data
        else:
            return data

    @classmethod
    def clear_extract_data(cls):
        cls.extract_data = {}