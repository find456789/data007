#!/usr/bin/env python
# -*- coding: utf-8 -*-
from models import db, mdb
from caches import LC

from datetime import datetime, timedelta
from bisect import bisect

from crawler.cates import cates

credits = [ 4, 11, 41, 91, 151, 
            251, 501, 1001, 2001, 5001, 
            10001, 20001, 50001, 100001, 200001,
            500001, 1000001, 2000001, 5000001, 10000001, ]

def aggregate_shop(shopid, date=datetime.utcnow()+timedelta(hours=8)):
    date2 = datetime(date.year, date.month, date.day)
    date1 = date2 - timedelta(days=1)
    date0 = date2 - timedelta(days=2)
    datep = date2 - timedelta(days=3)
    date60 = date2 - timedelta(days=60)
    si = db.execute('''select id, date, iid from ataobao2.shop_by_item 
                        where id=:shopid and date>=:datep and date<:date2''',
                dict(shopid=shopid, datep=datep, date2=date2), result=True)

    # if there is no info about the provided shopid
    # we do nothing
    if not si.results:
        return

    itemids = set(r[2] for r in si.results)
    cids = db.execute('''select id, cid from ataobao2.item where id in :ids''', dict(ids=tuple(itemids)), result=True)
    items = db.execute('''select id, date, price, num_sold30, num_collects, num_reviews, num_views from ataobao2.item_by_date
                          where id in :ids and date>=:datep and date<:date2''',
                    dict(ids=tuple(itemids), datep=datep, date2=date2), result=True)
    shop = db.execute('''select title, logo, rank_num from ataobao2.shop where id=:shopid''', 
                        dict(shopid=shopid), result=True) 

    ciddict = dict(cids.results)

    item_metrics = calculate_item_metrics(items.results)
    plans = calculate_aggregations(ciddict, item_metrics, shopid, shop)
    insert_plans(plans) 

def insert_plans(plans):
    for pname in plans:
        print('insert into {}: {}'.format(pname, plans[pname]))
        mdb[pname].save(plans[pname]) 

def calculate_aggregations(ciddict, item_metrics, shopid, shop):
    cids = ciddict.values()
    l1l2 = get_l1_and_l2_cids(cids)
    plans = {}
    for itemid in item_metrics:
        cid = ciddict[itemid]
        m = item_metrics[itemid]
        for pname in ['shop_{}_mon'.format(l1l2[cid][0]), 'shop_{}_{}_mon'.format(l1l2[cid][0], l1l2[cid][1]), 'shop_base']:
            if pname not in plans:
                plans[pname] = {
                    '_id': shopid,
                    'active_index': m['active_index'],
                    'delta_active_index': m['delta_active_index'],
                    'deals': m['deals'],
                    'delta_deals': m['delta_deals'],
                    'sales': m['price']*m['deals'],
                }
            else:
                plans[pname]['active_index'] += m['active_index']
                plans[pname]['delta_active_index'] += m['delta_active_index']
                plans[pname]['deals'] += m['deals']
                plans[pname]['delta_deals'] += m['delta_deals']
                plans[pname]['sales'] += m['price'] * m['deals']

    if plans:
        pname = 'shop_base'
        plans[pname]['worth'] = 10 * (plans[pname]['active_index']/1000. + plans[pname]['sales']/30.*0.3)
        if shop.results:
            plans[pname]['name'] = shop.results[0][0]
            plans[pname]['logo'] = shop.results[0][1]
            plans[pname]['credit_score'] = bisect(credits, shop.results[0][2])

    for pname in plans:
        plans[pname]['score'] = plans[pname]['active_index']/1000. + plans[pname]['sales']/30.*0.3
        for field in ['worth', 'credit_score', 'active_index']:
            plans[pname][field] = plans['shop_base'][field]
    return plans
       
   
def get_l1_and_l2_cids(cids): 
    l1l2 = {}
    for cid in cids:
        if cid in cates:
            cidchain = []
            while cates[cid] != 0:
                cidchain.append(cid)
                cid = cates[cid]
            cidchain.append(cid)
            l1l2[ cidchain[0] ] = (cidchain[-1], cidchain[-2])
    return l1l2

def calculate_item_metrics(items):
    itemdate = {}
    ids = set()
    metrics = {}
    for id, date, price, num_sold30, num_collects, num_reviews, num_views in items:
        date = date.strftime("%Y-%m-%d")
        if date not in itemdate:
            itemdate[date] = {}
        itemdate[date][id] = (price, num_sold30, num_collects, num_reviews, num_views)
        ids.add(id)

    dates = sorted(itemdate.keys())

    try:
        d1, d2, d3 = dates
    except:
        return {}

    # fixing data
    for id in ids:
        if id in itemdate[d1]:
            if id not in itemdate[d2]:
                itemdate[d2][id] = itemdate[d1][id] 
            if id not in itemdate[d3]:
                itemdate[d3][id] = itemdate[d1][id] 
        if id in itemdate[d2]:
            if id not in itemdate[d3]:
                itemdate[d3][id] = itemdate[d2][id]
            if id not in itemdate[d1]:
                itemdate[d1][id] = itemdate[d2][id]
        if id in itemdate[d3]:
            if id not in itemdate[d1]:
                itemdate[d1][id] = itemdate[d3][id]
            if id not in itemdate[d2]:
                itemdate[d2][id] = itemdate[d3][id]

    # do calc
    for id in ids: 
        data1, data2, data3 = itemdate[d1][id], itemdate[d2][id], itemdate[d3][id]
        active_index = (data3[2] - data2[2])*50 + (data3[3] - data2[3])*10 + (data3[4] - data2[4])
        delta_active_index = active_index - ((data2[2] - data1[2])*50 + (data2[3] - data1[3])*10 + (data2[4] - data1[4]))
        deals = data3[1]
        delta_deals = data3[1] - data2[1]
        metrics[id] = dict(active_index=active_index, delta_active_index=delta_active_index, deals=deals, delta_deals=delta_deals, price=price)
    return metrics

if __name__ == '__main__':
    aggregate_shop(102603268)
