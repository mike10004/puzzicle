#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time
from typing import Optional, Callable, Any

from puzzicle.puzzicon.fill import Answer
from puzzicle.puzzicon.fill.bank import Bank
from puzzicle.puzzicon.fill.state import FillState

_log = logging.getLogger(__name__)
_CONTINUE = False
_STOP = True

class FillListener(object):

    def __init__(self, node_threshold: int=None, duration_threshold: float=None):
        self.node_threshold = node_threshold
        self.count = 0
        self.start = None
        self.duration_threshold = duration_threshold

    def accept(self, state: FillState, bank: Bank):
        if self.start is None:
            self.start = time.perf_counter()
        keep_going = self.check_state(state, bank)
        self.count += 1
        if keep_going != _CONTINUE:
            result = _STOP
        elif self.is_over_threshold():
            result = _STOP
        else:
            result = _CONTINUE
        return result

    def check_state(self, state: FillState, bank: Bank):
        raise NotImplementedError("subclass must implement")

    def is_over_threshold(self):
        if self.node_threshold is not None:
            if self.count >= self.node_threshold:
                return True
        if self.duration_threshold is not None and self.start is not None:
            duration = time.perf_counter() - self.start
            if duration >= self.duration_threshold:
                return True
        return False

    def value(self):
        raise NotImplementedError("subclass must implement")

class FirstCompleteListener(FillListener):

    def __init__(self, node_threshold: int=None, duration_threshold: float=None):
        super().__init__(node_threshold, duration_threshold)
        self.completed = None

    def check_state(self, state: FillState, bank: Bank):
        if state.is_complete():
            self.completed = state
            return _STOP
        return _CONTINUE

    def value(self):
        return self.completed


class AllCompleteListener(FillListener):

    def __init__(self, node_threshold: int=None, duration_threshold: float=None):
        super().__init__(node_threshold, duration_threshold)
        self.completed = set()

    def value(self):
        return self.completed

    def check_state(self, state: FillState, bank: Bank):
        if state.is_complete():
            self.completed.add(state)
        return _CONTINUE


class FillStateNode(object):

    def __init__(self, state: FillState, parent: 'FillStateNode'=None):
        self.state: FillState = state
        self.parent: Optional[FillStateNode] = parent
        self.known_unfillable: bool = False


class Filler(object):

    def __init__(self, bank: Bank, tracer: Optional[Callable[[FillStateNode], Any]]=None):
        self.bank = bank
        self.tracer = tracer
        self.sorter: Optional[Callable[[Answer], Any]] = None

    def fill(self, state: FillState, listener: FillListener=None) -> FillListener:
        listener = listener or FirstCompleteListener()
        self._fill(FillStateNode(state), listener)
        return listener

    def _fill(self, node: FillStateNode, listener: FillListener) -> bool:
        if self.tracer is not None:
            self.tracer(node)
        if listener.accept(node.state, self.bank) == _STOP:
            return _STOP
        action_flag = _CONTINUE
        for answer_idx in node.state.provide_unfilled(self.sorter):
            for suggestion in self.bank.suggest(node.state, answer_idx):
                new_state = node.state.advance(suggestion)
                new_node = FillStateNode(new_state, node)
                continue_now =  self._fill(new_node, listener)
                if continue_now != _CONTINUE:
                    action_flag = _STOP
                    break
            if action_flag == _STOP:
                break
        return action_flag

