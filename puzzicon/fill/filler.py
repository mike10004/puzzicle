#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Tuple, List, Sequence, Dict, Optional, Iterator, Callable, Any
import logging
from puzzicon.fill.state import FillState
from puzzicon.fill.bank import Bank

_log = logging.getLogger(__name__)
_CONTINUE = False
_STOP = True

class FillListener(object):

    def __init__(self, threshold: int=None, notify: Optional[Callable[['FillListener', FillState, Bank, bool], None]]=None):
        self.threshold = threshold
        self.count = 0
        self.notify = notify

    def __call__(self, state: FillState, bank: Bank):
        keep_going = self.check_state(state, bank)
        self.count += 1
        if keep_going != _CONTINUE:
            result = _STOP
        elif self.is_over_threshold():
            result = _STOP
        else:
            result = _CONTINUE
        if self.notify is not None:
            self.notify(self, state, bank, result)
        return result

    def check_state(self, state: FillState, bank: Bank):
        raise NotImplementedError("subclass must implement")

    def is_over_threshold(self):
        return self.threshold is not None and self.count >= self.threshold

    def value(self):
        raise NotImplementedError("subclass must implement")

class FirstCompleteListener(FillListener):

    def __init__(self, threshold: int=None):
        super().__init__(threshold)
        self.completed = None

    def check_state(self, state: FillState, bank: Bank):
        if state.is_complete():
            self.completed = state
            return _STOP
        return _CONTINUE

    def value(self):
        return self.completed


class AllCompleteListener(FillListener):

    def __init__(self, threshold: int=None):
        super().__init__(threshold)
        self.completed = set()

    def value(self):
        return self.completed

    def check_state(self, state: FillState, bank: Bank):
        if state.is_complete():
            self.completed.add(state)
        return _CONTINUE


class FillStateNode(object):

    def __init__(self, state: FillState, parent: 'FillStateNode'=None):
        self.state = state
        self.parent = parent
        self.known_unfillable = False


class Filler(object):

    def __init__(self, bank: Bank, tracer: Optional[Callable[[FillStateNode], Any]]=None):
        self.bank = bank
        self.tracer = tracer

    def fill(self, state: FillState, listener: FillListener=None) -> FillListener:
        listener = listener or FirstCompleteListener()
        self._fill(FillStateNode(state), listener)
        return listener

    def _fill(self, node: FillStateNode, listener: Callable[[FillState, Bank], bool]) -> bool:
        if self.tracer is not None:
            self.tracer(node)
        if listener(node.state, self.bank) == _STOP:
            return _STOP
        action_flag = _CONTINUE
        for template_idx in node.state.unfilled():
            for legend_updates in self.bank.suggest_updates(node.state, template_idx):
                new_state = node.state.advance_unchecked(legend_updates)
                new_node = FillStateNode(new_state, node)
                continue_now =  self._fill(new_node, listener)
                if continue_now != _CONTINUE:
                    action_flag = _STOP
                    break
            if action_flag == _STOP:
                break
        return action_flag

