#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abmapper import app, db
from abmapper.lib import country_colours
from abmapper.lib import util
import projects as abprojects

def budget_project_stats(country_code, budget_type):
    # GET SQL
    # CALCULATE BEFORE, AFTER
    sql = """
    SELECT sum(atransaction.value*sector.percentage/100) AS sum_value,
    budgetcode.code, budgetcode.name
    FROM atransaction
    JOIN activity ON 
        activity.iati_identifier=atransaction.activity_iati_identifier
    JOIN sector ON 
        activity.iati_identifier = sector.activity_iati_identifier
    JOIN dacsector ON sector.code = dacsector.code
    JOIN commoncode ON dacsector.cc_id = commoncode.id
    JOIN ccbudgetcode ON commoncode.id = ccbudgetcode.cc_id
    JOIN budgetcode ON ccbudgetcode.budgetcode_id = budgetcode.id
    WHERE sector.deleted = 0
    AND activity.recipient_country_code="%s"
    AND activity.aid_type_code IN ('C01', 'D01', 'D02')
    AND activity.status_code IN (2, 3)
    AND atransaction.transaction_type_code="C"
    AND budgetcode.country_code = "%s"
    AND budgetcode.budgettype_code = "%s"
    GROUP BY budgetcode.code
    ;"""

    sql_before = """
    SELECT sum(atransaction.value*sector.percentage/100) AS sum_value,
    budgetcode.code, budgetcode.name
    FROM atransaction
    JOIN activity ON activity.iati_identifier=atransaction.activity_iati_identifier
    JOIN sector ON activity.iati_identifier = sector.activity_iati_identifier
    JOIN dacsector ON sector.code = dacsector.code
    JOIN commoncode ON dacsector.cc_id = commoncode.id
    JOIN ccbudgetcode ON commoncode.id = ccbudgetcode.cc_id
    JOIN budgetcode ON ccbudgetcode.budgetcode_id = budgetcode.id
    WHERE sector.edited = 0
    AND activity.recipient_country_code="%s"
    AND activity.aid_type_code IN ('C01', 'D01', 'D02')
    AND activity.status_code IN (2, 3)
    AND atransaction.transaction_type_code="C"
    AND budgetcode.country_code = "%s"
    AND budgetcode.budgettype_code = "%s"
    GROUP BY budgetcode.code
    ;"""

    sql_total = """
    SELECT sum(atransaction.value) AS sum_value
    FROM atransaction
    JOIN activity ON 
        activity.iati_identifier=atransaction.activity_iati_identifier
    AND activity.recipient_country_code="%s"
    AND activity.aid_type_code IN ('C01', 'D01', 'D02')
    AND activity.status_code IN (2, 3)
    AND atransaction.transaction_type_code="C"
    ;"""

    after = db.engine.execute(sql % (
                country_code, country_code, budget_type)
                )
    before = db.engine.execute(sql_before % (
                country_code, country_code, budget_type)
                )
    total = db.engine.execute(sql_total % (
                country_code
                )).first()[0]

    stats = {'total': total,
             'budgets': {}}
        
    unknown_value_before = total
    unknown_value_after = total

    for b in before:
        if b.code not in stats['budgets']:
            stats['budgets'][b.code] = {
                'code': util.nulltoDash(b.code),
                'name': util.nulltoUnknown(b.name),
                'after': {'value': 0.00, 'pct': 0.00}
            }
        stats['budgets'][b.code]['before'] = {
                'value': b.sum_value,
                'pct': round(float(b.sum_value)/total*100, 2)
                }
        unknown_value_before -= b.sum_value
    for a in after:
        if a.code not in stats['budgets']:
            stats['budgets'][a.code] = {
                'code': util.nulltoDash(a.code),
                'name': util.nulltoUnknown(a.name),
                'before': {'value': 0.00, 'pct': 0.00
                }
            }
        stats['budgets'][a.code]['after'] = {
                'value': a.sum_value,
                'pct': round(float(a.sum_value)/total*100, 2)
                }
        unknown_value_after -= a.sum_value

    stats["budgets"]["-"] = {
        'code': '-',
        'name': "Unknown",
        'before': {
            'value': unknown_value_before,
            'pct': round(float(unknown_value_before)/total*100, 2)
        },
        'after': {
            'value': unknown_value_after,
            'pct': round(float(unknown_value_after)/total*100, 2)
        }
    }

    for code, budget in stats['budgets'].items():
        try:
            stats['budgets'][code]['change_pct'] = round(
            ((budget['after']['value']-budget['before']['value']
                ) / budget['before']['value']) * 100, 2)
        except ZeroDivisionError:
            stats['budgets'][code]['change_pct'] = "NEW"
            
        if stats['budgets'][code]['change_pct'] == 0.0:
            stats['budgets'][code]['change_pct'] = ""

        stats['budgets'][code]['before']['value'] = "{:,.2f}".format(stats['budgets'][code]['before']['value'])
        stats['budgets'][code]['after']['value'] = "{:,.2f}".format(stats['budgets'][code]['after']['value'])

    after.close()
    before.close()
    return stats
    
def get_colour(node, ccolours):
    if ccolours:
        if node in ccolours: return ccolours[node]
    return node

def generate_sankey_data(country_code, budget_type):
    sql_reporting_org_cc = """
    SELECT sum(atransaction.value*sector.percentage/100) AS sum_value,
    activity.reporting_org_ref, commoncode.category_EN
    FROM atransaction
    JOIN activity ON
        activity.iati_identifier=atransaction.activity_iati_identifier
    JOIN sector ON
        activity.iati_identifier = sector.activity_iati_identifier
    LEFT JOIN dacsector ON sector.code = dacsector.code
    LEFT JOIN commoncode ON dacsector.cc_id = commoncode.id
    LEFT JOIN ccbudgetcode ON commoncode.id = ccbudgetcode.cc_id
    LEFT JOIN budgetcode ON ccbudgetcode.budgetcode_id = budgetcode.id
    WHERE sector.deleted = 0
    AND activity.recipient_country_code="%s"
    AND activity.aid_type_code IN ('C01', 'D01', 'D02')
    AND activity.status_code IN (2, 3)
    AND atransaction.transaction_type_code="C"
    AND budgetcode.country_code="%s"
    AND budgetcode.budgettype_code = "%s"
    GROUP BY commoncode.category_EN, activity.reporting_org_ref
    ;"""
            
    sql_cc_budgetcode = """
    SELECT sum(atransaction.value*sector.percentage/100) AS sum_value,
    budgetcode.code, budgetcode.name, commoncode.category_EN
    FROM atransaction
    JOIN activity ON
        activity.iati_identifier=atransaction.activity_iati_identifier
    JOIN sector ON
        activity.iati_identifier = sector.activity_iati_identifier
    LEFT JOIN dacsector ON sector.code = dacsector.code
    LEFT JOIN commoncode ON dacsector.cc_id = commoncode.id
    LEFT JOIN ccbudgetcode ON commoncode.id = ccbudgetcode.cc_id
    LEFT JOIN budgetcode ON ccbudgetcode.budgetcode_id = budgetcode.id
    WHERE sector.deleted = 0
    AND activity.recipient_country_code="%s"
    AND activity.aid_type_code IN ('C01', 'D01', 'D02')
    AND activity.status_code IN (2, 3)
    AND atransaction.transaction_type_code="C"
    AND budgetcode.country_code="%s"
    AND budgetcode.budgettype_code = "%s"
    GROUP BY budgetcode.code, commoncode.category_EN
    ;"""

    reporting_org_cc = db.engine.execute(sql_reporting_org_cc % (
            country_code, country_code, budget_type)
            )
    cc_budgetcode = db.engine.execute(sql_cc_budgetcode % (
            country_code, country_code, budget_type)
            )
    
    node_data = {
        "known": {},
        "num_known": 0
    }
    links = []
    
    def notNull(value, typeof):
        if (value == None or value == "") and typeof == "category":
            return "Unmapped"
        if (value == None or value == "") and typeof == "budgetcode":
            return "Unknown budget code"
        return value
    
    def get_node_code(node_name, node_data):
        node_name = node_name
        if node_name not in node_data['known']:
            node_data['known'][node_name] = node_data['num_known']
            node_data['num_known'] += 1
        return node_data['known'][node_name]
    
    for rc in reporting_org_cc:
        links.append({
            'source': get_node_code(rc.reporting_org_ref, node_data),
            'target': get_node_code(
                    notNull(rc.category_EN, "category"), node_data
                    ),
            'value': rc.sum_value
        })
    
    for cb in cc_budgetcode:
        links.append({
            'source': get_node_code(
                notNull(cb.category_EN, "category"), node_data
                ),
            'target': get_node_code(
                notNull(cb.name, "budgetcode"), node_data
                ),
            'value': cb.sum_value
        })
        
    ccolours = country_colours.colours(country_code)

    nodes = [{'name': node,
              'colour': get_colour(node, ccolours)} for node in
               sorted(node_data['known'], key=node_data['known'].get)]

    from operator import itemgetter
    links = sorted(links, key=itemgetter('value'))

    out = {'nodes': nodes, 'links': links}

    reporting_org_cc.close()
    cc_budgetcode.close()

    return out

def country_project_stats(country_code, aid_types=["C01", "D01", "D02"], 
                                        activity_statuses=[2,3]):

    original_p = abprojects.projects(country_code)

    total_projects = len(original_p)

    def aid_type_filter(the_project):
        return (the_project.aid_type_code in aid_types) and (
                    the_project.status_code in activity_statuses)

    p = filter(aid_type_filter, original_p)

    filtered_projects = len(p)

    total_value = sum(map(lambda project:
         util.none_is_zero(project.total_commitments), original_p))
    total_filtered_value = sum(map(lambda project:
         util.none_is_zero(project.total_commitments), p))
    total_mappable_before = sum(map(lambda project:
         util.none_is_zero(project.pct_mappable_before)/100 *
                util.none_is_zero(project.total_commitments), p))
    total_mappable_after = sum(map(lambda project:
         util.none_is_zero(project.pct_mappable_after)/100 *
                util.none_is_zero(project.total_commitments), p))

    total_mappable_before_admin = sum(map(lambda project:
         util.none_is_zero(project.pct_mappable_before_admin)/100 *
                util.none_is_zero(project.total_commitments), p))
    total_mappable_after_admin = sum(map(lambda project:
         util.none_is_zero(project.pct_mappable_after_admin)/100 *
                util.none_is_zero(project.total_commitments), p))
    admin = bool(total_mappable_after_admin > 0)

    total_capital_before = 0.00
    total_capital_after = sum(map(lambda project:
        project.capital_exp * util.none_is_zero(project.total_commitments),
        filter(util.filter_none_out, p)))
    total_na_after = sum(map(lambda project: 1 * 
        util.none_is_zero(project.total_commitments),
        filter(util.filter_none_in, p)))
    total_current_after = (
        total_filtered_value -
        total_capital_after -
        total_na_after
        )
    return {
        "total_value": "{:,}".format(total_value),
        "total_filtered_value": "{:,}".format(total_filtered_value),
        "total_mappable_before": total_mappable_before,
        "total_mappable_before_pct": round(
            total_mappable_before/total_filtered_value*100, 2),
        "total_mappable_after": total_mappable_after,
        "total_mappable_after_pct": round(
            total_mappable_after/total_filtered_value*100, 2),
        "total_capital_before_pct": round(
            total_capital_before/total_filtered_value*100, 2),
        "total_capital_after_pct": round(
            total_capital_after/total_filtered_value*100, 2),
        "total_current_after_pct": round(
            total_current_after/total_filtered_value*100, 2),
        "total_projects": total_projects,
        "filtered_projects": filtered_projects,
        "admin": admin,
        "total_mappable_before_pct_admin": round(
            total_mappable_before_admin/total_filtered_value*100, 2),
        "total_mappable_after_pct_admin": round(
            total_mappable_after_admin/total_filtered_value*100, 2),
           }

def earliest_latest_disbursements(country_code):
    country = abprojects.country(country_code)
    FYDATA_QUERY = """
        SELECT strftime('%%Y', DATE(transaction_date, '-%s month'))
        AS fiscal_year
        FROM atransaction
        JOIN activity ON
            activity.iati_identifier=atransaction.activity_iati_identifier
        WHERE activity.recipient_country_code = '%s'
        AND atransaction.transaction_type_code = '%s'
        GROUP BY fiscal_year
        """
    fydata_results = db.engine.execute(FYDATA_QUERY % (
            country.fiscalyear_modifier, country_code, "D")
            )
    fydata = map(lambda d: int(d[0]), fydata_results)
    max_fydata = max(fydata)
    min_fydata = min(fydata)
    return min_fydata, max_fydata

def sectors_stats():
    # for each sector, count number of projects and value using that
    #  sector.
    sql = """
    SELECT
    dacsector.code, dacsector.description_EN,
    dacsector.parent_code,
    group_concat(activity.recipient_country_code) AS countries,
    sum(atransaction.value*sector.percentage/100) AS sum_value,
    count(activity.id) AS num_activities
    FROM dacsector
    LEFT JOIN sector ON sector.code = dacsector.code
    LEFT JOIN activity ON
        activity.iati_identifier = sector.activity_iati_identifier
    LEFT JOIN atransaction ON
        activity.iati_identifier=atransaction.activity_iati_identifier
    WHERE sector.deleted = 0
    AND atransaction.transaction_type_code='C'
    GROUP BY dacsector.code
    ;"""
    sector_stats_results = db.engine.execute(sql)

    def tidy_countries(countries):
        return ",".join(set(countries.split(",")))

    stats = []
    for sector in sector_stats_results:
        stats.append({
            "sector_code": sector.code,
            "sector_description": sector.description_EN,
            "sector_parent_code": sector.parent_code,
            "countries": tidy_countries(sector.countries),
            "total_value": round(sector.sum_value, 2),
            "num_activities": sector.num_activities
        })
    return stats
