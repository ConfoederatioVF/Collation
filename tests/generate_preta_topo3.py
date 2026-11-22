import json
import re
import unicodedata

# 1. Load antigas denominações
with open('tests/parsed_antigas_denominacoes.json', 'r', encoding='utf-8') as f:
    antigas = json.load(f)

def norm(s):
    if not s: return ''
    s = str(s).strip()
    return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII').lower()

antigas_map = {}
for state, items in antigas.items():
    for it in items:
        antigas_map[norm(it['current'])] = it

# 2. Known manual fixes for canonical names and diacritics
CANONICAL_NAME_FIXES = {
    'Antonio Bezerra-Brazil': 'Antônio Bezerra',
    'Capuáva-Brazil': 'Capuava',
    'Nova Brasilia-Brazil': 'Nova Brasília',
    'São José-Brazil': 'São José',
    'Jardim Angela-Brazil': 'Jardim Ângela',
    'Capao Redondo-Brazil': 'Capão Redondo',
    'Embu-Brazil': 'Embu das Artes',
    'Jardim Sao Luis-Brazil': 'Jardim São Luís',
    'Brasilandia-Brazil': 'Brasilândia',
    'Passo do Sabao-Brazil': 'Passo do Sabão',
    'Sao Rafael-Brazil': 'São Rafael',
    'Cangaiba-Brazil': 'Cangaíba',
    'Vila Curuca-Brazil': 'Vila Curuçá',
    'Cidade Lider-Brazil': 'Cidade Líder',
    'Vila Jacui-Brazil': 'Vila Jacuí',
    'Jose Bonifacio-Brazil': 'José Bonifácio',
    'Butanta-Brazil': 'Butantã',
    'Eunápolls-Brazil': 'Eunápolis',
    'Campos Elisios-Brazil': 'Campos Elíseos',
    'Aparecida de Goiánia-Brazil': 'Aparecida de Goiânia',
    'Augusto Severo (Campo Grande)-Brazil': 'Campo Grande',
    'Januário Cicco (Boa Saúde)-Brazil': 'Boa Saúde',
    'Miracema do Norte-Brazil': 'Miracema do Tocantins',
    'Lago Verde (MA)-Brazil': 'Lago Verde',
    'Planaltina (Distrito Federal)-Brazil': 'Planaltina'
}

print("Loaded base mappings successfully.")
