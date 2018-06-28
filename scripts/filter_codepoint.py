import json
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('--hans-in', type=str, required=True)
parser.add_argument('--hans-out', type=str, required=True)
args = parser.parse_args()
print(args)


FILTER_LIST = [
    # CJK_Unified_Ideographs_Extension_B
    (0x20000, 0x2A6DF),
    # CJK_Unified_Ideographs_Extension_C
    (0x2A700, 0x2B73F),
]


def good_paragraph(pg):
    good = True
    for c in pg['context']:
        for codepoint in FILTER_LIST:
            if codepoint[0] <= ord(c) <= codepoint[1]:
                good = False
        if not good:
            break
    return good


with open(args.hans_in) as fin:
    data = json.load(fin)
    for doc in data['data']:
        doc['paragraphs'] = list(filter(good_paragraph, doc['paragraphs']))


with open(args.hans_out, 'w') as fout:
        json.dump(data, fout)
