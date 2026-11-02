"""Bounded local clearance; no portfolio simulation; stdout contains aggregates only."""
import ast
import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
START, END = '2025-09-18', '2026-10-30'

def history_state(stock_dates, spy_dates, day, required=270):
    s = sorted(d for d in stock_dates if d <= day)
    b = sorted(d for d in spy_dates if d <= day)
    if len(s) < required or len(b) < required:
        return 'PIT_ELIGIBLE_NO_SIGNAL_WARMUP'
    if s[-required:] != b[-required:] or s[-1] != day:
        return 'BLOCKED_CALENDAR_ALIGNMENT'
    return 'HISTORY_READY_NOT_SIGNAL_PROVEN'

def hypothesis(amount, expected):
    return amount is not None and abs(amount-expected) <= .01

def main():
    import pandas as pd
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='batch4a_full_v1_20261102.sqlite')
    parser.add_argument('--output',default='batch4a7_clearance_v2.json')
    args=parser.parse_args()
    private = ROOT/'restricted_norgate'
    if Path(args.db).name!=args.db or Path(args.output).name!=args.output:
        parser.error('Use basenames inside restricted_norgate')
    output = private/args.output
    if output.exists():
        raise FileExistsError('Choose a new version; private audit exists')
    db = private/args.db
    conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    sec = {r['asset_id']:dict(r) for r in conn.execute('select * from securities')}
    prices = {}
    for r in conn.execute('select * from prices order by asset_id,mode,date'):
        prices.setdefault((r['asset_id'],r['mode']),{})[r['date']] = dict(r)
    mem = {}
    for a,d,e in conn.execute('select asset_id,date,eligible from membership'):
        mem.setdefault(a,{})[d] = e
    spy = next(a for a,s in sec.items() if s['symbol']=='SPY')
    spy_dates = list(prices[spy,'NONE'])
    calendar = [d for d in spy_dates if START<=d<=END]
    members = {d:{a for a,m in mem.items() if m.get(d)==1} for d in calendar}
    anomalies=[]
    previous=set()
    for i,d in enumerate(calendar):
        if len(members[d])!=503:
            nearby = calendar[max(0,i-1):min(len(calendar),i+2)]
            changed=set().union(*(members[x] ^ members[d] for x in nearby))
            # Raw identity/date sets stay in the ignored file; no invented class mapping.
            anomalies.append({'date':d,'count':len(members[d]),
                'observed_member_identities':[{'asset_id':a,'symbol':sec[a]['symbol'],'share_class':'NOT_VERIFIED'} for a in sorted(members[d])],
                'nearby_membership_changes':[{'asset_id':a,'symbol':sec[a]['symbol'],
                    'observed_flags':{x:mem[a].get(x) for x in nearby},
                    'effective_date_verified':False,'share_class_verified':False} for a in sorted(changed)],
                'possible_missing_or_terminal_members':[{'asset_id':a,'symbol':sec[a]['symbol']} for a,m in mem.items()
                    if m and max(m)<d and m[max(m)]==1],
                'status':'PARTIAL_OBSERVED_FLAGS_NOT_INDEX_NOTICE'})
        previous=members[d]
    counts=Counter(); short={}; ready={}
    for a,s in sec.items():
        if not s['is_candidate']: continue
        dates=list(prices.get((a,'NONE'),{})); states=Counter(); ready[a]=[]
        for d in calendar:
            if mem.get(a,{}).get(d)!=1: continue
            if bisect_left(dates,d)<126: counts['member_dates_lt126_prior']+=1
            state=history_state(dates,spy_dates,d)
            states[state]+=1; counts[state]+=1
            if state=='HISTORY_READY_NOT_SIGNAL_PROVEN': ready[a].append(d)
        if states.get('PIT_ELIGIBLE_NO_SIGNAL_WARMUP'):
            short[a]={'symbol':s['symbol'],'counts':dict(states),'first_history_ready':next(iter(ready[a]),None)}
    # Extract only pure frozen feature definitions. Do not import/run any runner.
    fma=Path.home()/'FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41'
    source=fma/'momentum_pullback_breakout.py'
    snapshot=json.loads((ROOT/'configs/mpb_exit_reference.json').read_text())
    for name,expected in snapshot['source_sha256'].items():
        if hashlib.sha256((fma/name).read_bytes()).hexdigest()!=expected:
            raise RuntimeError('FROZEN_SOURCE_HASH_MISMATCH')
    tree=ast.parse(source.read_text())
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('bars','signal_features')]
    # Config module contains declarations; read its two needed thresholds via AST execution.
    import importlib.util
    spec=importlib.util.spec_from_file_location('batch4a7_frozen_config',fma/'config.py')
    config=importlib.util.module_from_spec(spec); sys.modules[spec.name]=config; spec.loader.exec_module(config)
    import numpy as np
    ns={'pd':pd,'np':np,'CFG':SimpleNamespace(min_history=270,momentum_sessions=(21,63,126),
        momentum_weights=(.25,.35,.40),consolidation_sessions=10,max_consolidation_range=.12,
        max_pullback=.12,ema_support_tolerance=.02,breakout_buffer=.001,breakout_volume_ratio=1.2,
        pullback_volume_ratio=1.,stop_atr_buffer=.25,min_stop_fraction=.015,max_stop_fraction=.10),
        'STRAT':config.STRAT,'CONTEST':config.CONTEST}
    # Verify config defaults against frozen class without importing its dependencies.
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PullbackConfig')
    for n in cls.body:
        if isinstance(n,ast.AnnAssign) and n.target.id in vars(ns['CFG']):
            if ast.literal_eval(n.value)!=getattr(ns['CFG'],n.target.id): raise RuntimeError('FEATURE_CONFIG_MISMATCH')
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(source),'exec'),ns)
    def frame(a):
        rows=list(prices.get((a,'TOTALRETURN'),{}).values())
        if not rows: return None
        p=pd.DataFrame(rows).set_index('date'); p.index=pd.to_datetime(p.index)
        return p.rename(columns={x:x.title() for x in ('open','high','low','close','volume')})
    benchmark=frame(spy); terminals=[]
    for a,s in sec.items():
        if s['status']!='DELISTED_DATABASE' or not s['is_candidate']: continue
        raw=prices.get((a,'NONE'),{}); dates=list(raw); last=dates[-1] if dates else None
        feature_days=[]; p=frame(a)
        for d in ready.get(a,[]):
            if last and d<last and p is not None:
                result=ns['signal_features'](p.loc[:d],benchmark.loc[:d],pd.Timestamp(d))
                if result and 'entry_confirmed' not in result:
                    raise RuntimeError('FROZEN_SIGNAL_SCHEMA_MISMATCH')
                if result.get('entry_confirmed'): feature_days.append(d)
        terminals.append({'asset_id':a,'symbol':s['symbol'],'last_price_date':last,
            'last_bar_member':mem.get(a,{}).get(last), 'history_ready_decision_days':len(ready.get(a,[])),
            'frozen_feature_eligible_before_terminal':feature_days,
            'exposure_bound':'POSSIBLE_ENTRY_TERMINAL_REVIEW' if feature_days else 'NO_ENTRY_UNDER_CURRENT_EXTRACT_EMPTY_START_ONLY',
            'actual_holdings':'UNKNOWN_NO_PIT_PATH_RUN', 'settlement':'BLOCKED_TERMS_AND_PAYMENT_UNVERIFIED',
            'scope':'Current extract only; deeper warmup or changed feature view invalidates exclusion'})
    prior=json.loads((private/'batch4a_actions_v3_20261102.json').read_text())
    symbols={s['symbol']:a for a,s in sec.items()}; exceptions=[]; div_counts=Counter()
    for e in prior['private_dividend_exceptions']:
        a=symbols[e['symbol']]; ex=e['ex_date']; dates=list(prices[a,'NONE']); ix=bisect_left(dates,ex)
        ent=dates[ix-1] if ix else None
        modes={m:prices.get((a,m),{}).get(ent) for m in ('NONE','CAPITAL','CAPITALSPECIAL','TOTALRETURN')}
        raw=modes['NONE']; cap=modes['CAPITAL']; special=modes['CAPITALSPECIAL']
        matches=[m for m,r in modes.items() if r and hypothesis(r['dividend'],e['legacy_amount'])]
        ratio=cap['close']/raw['close'] if raw and cap else None
        candidate=bool(raw and cap and cap['dividend'] is not None and ratio and hypothesis(cap['dividend']/ratio,e['legacy_amount']))
        div_counts['mode_match_hypotheses']+=bool(matches)
        div_counts['capital_factor_normalization_hypotheses']+=candidate
        exceptions.append({**e,'asset_id':a,'entitlement_date':ent,'next_observed_date':dates[ix] if ix<len(dates) else None,
            'exact_exdate_bar':ex in dates,'mode_entitlement_rows':modes,
            'neighboring_raw_rows':{d:prices[a,'NONE'][d] for d in dates[max(0,ix-2):ix+2]},
            'matching_modes_hypothesis_only':matches,'capital_to_raw_factor':ratio,
            'factor_normalization_match_hypothesis_only':candidate,
            'ordinary_special_residual_difference':cap['dividend']-special['dividend'] if cap and special and cap['dividend'] is not None and special['dividend'] is not None else None,
            'record_date':None,'payment_date':None,'independent_event_terms':None,
            'status':'PARTIAL_NOT_CLEARED'})
    summary={'membership_exception_dates':len(anomalies),'warmup':dict(counts),
        'warmup_affected_securities':len(short),'dividend_exceptions':len(exceptions),
        'dividend_hypotheses':dict(div_counts),'independently_cleared_dividends':0,
        'delisted_candidates':len(terminals),'last_bar_member_one':sum(t['last_bar_member']==1 for t in terminals),
        'terminal_candidates_with_possible_feature_entry':sum(bool(t['frozen_feature_eligible_before_terminal']) for t in terminals),
        'actual_PIT_holdings_verified':False,'READY_FOR_4B':False}
    report={'summary':summary,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'db_sha256':hashlib.sha256(db.read_bytes()).hexdigest(),'frozen_feature_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'membership_review':anomalies,'warmup_review':short,'dividend_review':exceptions,'terminal_review':terminals}
    with output.open('x') as f: json.dump(report,f,indent=2)
    print(json.dumps(summary,indent=2))
    conn.close()

if __name__=='__main__': main()
