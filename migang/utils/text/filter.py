#!/usr/bin/env python
# -*- coding:utf-8 -*-

# ref: https://github.com/observerss/textfilter

import re
from typing import Union
from collections import defaultdict

from nonebot.adapters.onebot.v11 import Message

from migang.core import TEXT_PATH

__all__ = ["NaiveFilter", "BSFilter", "DFAFilter"]
__author__ = "observer"
__date__ = "2012.01.05"


class NaiveFilter:

    """Filter Messages from keywords

    very simple filter implementation

    >>> f = NaiveFilter()
    >>> f.add("sexy")
    >>> f.filter("hello sexy baby")
    hello **** baby
    """

    def __init__(self):
        self.keywords = set([])

    def parse(self, path):
        for keyword in open(path, encoding="utf8"):
            self.keywords.add(keyword.strip().decode("utf-8").lower())

    def filter(self, message, repl="*"):
        message = message.lower()
        for kw in self.keywords:
            message = message.replace(kw, repl)
        return message


class BSFilter:

    """Filter Messages from keywords

    Use Back Sorted Mapping to reduce replacement times

    >>> f = BSFilter()
    >>> f.add("sexy")
    >>> f.filter("hello sexy baby")
    hello **** baby
    """

    def __init__(self):
        self.keywords = []
        self.kwsets = set([])
        self.bsdict = defaultdict(set)
        self.pat_en = re.compile(r"^[0-9a-zA-Z]+$")  # english phrase or not

    def add(self, keyword):
        # if not isinstance(keyword, unicode):
        #     keyword = keyword.decode('utf-8')
        keyword = keyword.lower()
        if keyword not in self.kwsets:
            self.keywords.append(keyword)
            self.kwsets.add(keyword)
            index = len(self.keywords) - 1
            for word in keyword.split():
                if self.pat_en.search(word):
                    self.bsdict[word].add(index)
                else:
                    for char in word:
                        self.bsdict[char].add(index)

    def parse(self, path):
        with open(path, "r", encoding="utf8") as f:
            for keyword in f:
                self.add(keyword.strip())

    def filter(self, message, repl="*"):
        # if not isinstance(message, unicode):
        #     message = message.decode('utf-8')
        message = message.lower()
        for word in message.split():
            if self.pat_en.search(word):
                for index in self.bsdict[word]:
                    message = message.replace(self.keywords[index], repl)
            else:
                for char in word:
                    for index in self.bsdict[char]:
                        message = message.replace(self.keywords[index], repl)
        return message


class DFAFilter:

    """Filter Messages from keywords

    Use DFA to keep algorithm perform constantly

    >>> f = DFAFilter()
    >>> f.add("sexy")
    >>> f.filter("hello sexy baby")
    hello **** baby
    """

    def __init__(self):
        self.keyword_chains = {}
        self.delimit = "\x00"

    def add(self, keyword):
        # if not isinstance(keyword, unicode):
        #     keyword = keyword.decode('utf-8')
        # keyword = keyword.lower()
        chars = keyword.strip()
        if not chars:
            return
        level = self.keyword_chains
        for i in range(len(chars)):
            if chars[i] in level:
                level = level[chars[i]]
            else:
                if not isinstance(level, dict):
                    break
                for j in range(i, len(chars)):
                    level[chars[j]] = {}
                    last_level, last_char = level, chars[j]
                    level = level[chars[j]]
                last_level[last_char] = {self.delimit: 0}
                break
        if i == len(chars) - 1:
            level[self.delimit] = 0

    def parse(self, path):
        with open(path, "r", encoding="utf8") as f:
            for keyword in f:
                self.add(keyword.strip())

    def filter(self, message, repl="*"):
        # if not isinstance(message, unicode):
        #     message = message.decode('utf-8')
        # message = message.lower()
        ret = []
        start = 0
        while start < len(message):
            level = self.keyword_chains
            step_ins = 0
            for char in message[start:]:
                if char in level:
                    step_ins += 1
                    if self.delimit not in level[char]:
                        level = level[char]
                    else:
                        ret.append(repl * step_ins)
                        start += step_ins - 1
                        break
                else:
                    ret.append(message[start])
                    break
            else:
                ret.append(message[start])
            start += 1

        return "".join(ret)


gfw = DFAFilter()
gfw.parse(TEXT_PATH / "sensitive_words.txt")


def filt_message(message: Union[Message, str]):
    if isinstance(message, str):
        return gfw.filter(message)
    elif isinstance(message, Message):
        for seg in message:
            if seg.type == "text":
                seg.data["text"] = gfw.filter(seg.data.get("text", ""))
        return message
    else:
        raise TypeError
