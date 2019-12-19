#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
from typing import Optional

import examples
from puzzicon.grid import GridModel
import puzzicon
import hashlib
import os
from puzzicon.fill.bank import Bank, BankSerializer

_expected = set(map(str.upper, ["act",
"are",
"snootiest",
"inamorata",
"tog",
"denim",
"tub",
"dim",
"baled",
"Mae",
"stalemate",
"detonator",
"sew",
"oer",
"annotates",
"coagulate",
"tom",
"aired",
"reanimate",
"estimator",
"sit",
"Tod",
"tam",
"below",
"BSD",
"den",
"eer",
"Mao",]))

def create_bank_from_wordlist_file(pathname, cache_dir, max_word_length: Optional[int]):
    puzzemes = puzzicon.read_puzzeme_set(pathname)
    if max_word_length is not None:
        puzzemes = filter(lambda p: len(p.canonical) <= max_word_length, puzzemes)
    bank = Bank.with_registry([p.canonical for p in puzzemes], debug=False)
    if cache_dir is not None:
        bank_pathname = get_cached_bank_pathname(pathname, cache_dir, max_word_length)
        os.makedirs(os.path.dirname(bank_pathname), exist_ok=True)
        BankSerializer().serialize_to_file(bank, bank_pathname)
        print("bank written to", bank_pathname)
    return bank

def get_cached_bank_pathname(wordlist_pathname, cache_dir, max_word_length: Optional[int]) -> str:
    max_word_length = max_word_length or 0
    h = hashlib.sha256()
    with open(wordlist_pathname, 'rb') as ifile:
        h.update(ifile.read())
    basename = h.hexdigest()
    return os.path.join(cache_dir, "bank-{}-{}.pickle".format(max_word_length, basename))

def create_bank(pathname, cache_dir, max_word_length: Optional[int]=None):
    cached_bank_pathname = get_cached_bank_pathname(pathname, cache_dir, max_word_length)
    try:
        bank = BankSerializer().deserialize_from_file(cached_bank_pathname)
        print("bank read from", cached_bank_pathname)
        return bank
    except FileNotFoundError:
        return create_bank_from_wordlist_file(pathname, cache_dir, max_word_length)

def main():
    grid = GridModel.build(".___.___." +
                           "_________" +
                           "_________" +
                           "___._____" +
                           ".___.___." +
                           "_____.___" +
                           "_________" +
                           "_________" +
                           ".___.___.")
    wordlist_pathname = '/usr/share/dict/words'
    # this_dir_basename = os.path.basename(os.path.dirname(os.getcwd()))
    cache_dir = os.path.join(os.getcwd(), '.cache')
    bank = create_bank(wordlist_pathname, cache_dir, 9)
    return examples.do_main_with_bank(grid, bank, 2500)

if __name__ == '__main__':
    exit(main())
