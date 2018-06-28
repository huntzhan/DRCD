from tempfile import NamedTemporaryFile
from copy import deepcopy
import json
from collections import defaultdict
import argparse

from sh import opencc


def _opencc(text, config='tw2s'):
    with NamedTemporaryFile() as file_in,  NamedTemporaryFile() as file_out:
        with open(file_in.name, 'w') as fout:
            fout.write(text)

        opts = [
            '--input', file_in.name,
            '--output', file_out.name,
            '--config', f'/usr/share/opencc/{config}.json'
        ]
        status = opencc(*opts)
        assert status.exit_code == 0

        with open(file_out.name) as fin:
            return fin.read()

def t2s_answer_start(context_hans, answer_hans, answer_start):
    '''
    return
    '''
    all_starts = []
    start = 0
    while True:
        start = context_hans.find(answer_hans, start)
        if start < 0:
            break
        all_starts.append(start)
        start += len(answer_hans)

    if not all_starts:
        return None

    closest_idx = 0
    closest_diff = float('inf')
    for start in all_starts:
        diff = abs(answer_start - start)
        if diff < closest_diff:
            closest_diff = diff
            closest_idx = start

    return closest_idx


def t2s_raw_json(json_in):
    with open(json_in) as fin:
        raw_json = fin.read()

    return json.loads(_opencc(raw_json))


def check_and_bp(obj, fwd_keys, check_fn):

    _APPLY_DPKEY = '__duplicate'

    def _assign_context(context, cur_key, next_obj):
        context[_APPLY_DPKEY][cur_key] += 1
        if context[_APPLY_DPKEY][cur_key] > 1:
            cur_key += f':{context[_APPLY_DPKEY][cur_key]}'

        assert cur_key not in context
        context[cur_key] = next_obj
        return cur_key

    def _undo_assign_context(context, cur_key, _cur_key):
        context[_APPLY_DPKEY][cur_key] -= 1
        context.pop(_cur_key)

    def _apply(context, cur_obj, fwd_key_idx, fwd_keys, check_fn):
        # stop condition.
        if fwd_key_idx == len(fwd_keys) - 1:
            final_key = fwd_keys[-1]
            # return None if invalid.
            cur_obj[final_key] = check_fn(context, cur_obj, final_key)
            return

        # context: { fwd_key -> obj, '__duplicate': { fwd_key -> count } }
        cur_key = fwd_keys[fwd_key_idx]
        for next_obj in cur_obj[cur_key]:
            _cur_key = _assign_context(context, cur_key, next_obj)
            _apply(context, next_obj, fwd_key_idx + 1, fwd_keys, check_fn)
            _undo_assign_context(context, cur_key, _cur_key)

    def _bp_none(cur_obj, fwd_key_idx, fwd_keys):
        if fwd_key_idx == len(fwd_keys) - 1:
            return

        cur_key = fwd_keys[fwd_key_idx]
        next_key = fwd_keys[fwd_key_idx + 1]
        filtered = []
        for next_obj in cur_obj[cur_key]:
            _bp_none(next_obj, fwd_key_idx + 1, fwd_keys)
            if next_obj[next_key]:
                filtered.append(next_obj)

        cur_obj[cur_key] = filtered or None

    # 1. apply the check_fn.
    _apply(
        {_APPLY_DPKEY: defaultdict(int)},
        obj,
        0, fwd_keys,
        check_fn,
    )

    # 2. remove all invalid object.
    _bp_none(obj, 0, fwd_keys)


def t2s_squad_data(json_in, json_out):

    def check_fn(context, final_obj, final_key):
        assert final_key == 'answer_start'
        return t2s_answer_start(
            context['paragraphs']['context'],
            final_obj['text'],
            final_obj['answer_start']
        )

    data = t2s_raw_json(json_in)

    check_and_bp(
        data,
        ['data', 'paragraphs', 'qas', 'answers', 'answer_start'],
        check_fn,
    )

    with open(json_out, 'w') as fout:
        json.dump(data, fout, ensure_ascii=False)


parser = argparse.ArgumentParser()
parser.add_argument('--hant-in', type=str, required=True)
parser.add_argument('--hans-out', type=str, required=True)
args = parser.parse_args()
print(args)

# python scripts/t2s_squad.py --hant-in ./hant/DRCD_training.json --hans-out ./hans/DRCD_training.json
# python scripts/t2s_squad.py --hant-in ./hant/DRCD_dev.json --hans-out ./hans/DRCD_dev.json
t2s_squad_data(args.hant_in, args.hans_out)
