"""Property taxes the Nederland fire, library and EcoPass districts collect from the Eldora sellers' property.

`python3 scripts/district_taxes.py --build` reads the Boulder County Assessor files kept in private/assessor
(not in the repository) and writes analysis/district_taxes.json (category totals and district estimates).
The page itself only reads that file (html()).

Sources: Boulder County Assessor account data (Oct. 17, 2026, download); Boulder County Treasurer account pages for the three largest accounts (2025 values, taxes billed in 2026);
the Assessor's 2025 mill levy file and 2025 certifications of value to each district.
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIV = os.path.join(ROOT, 'private', 'assessor')
OUT_JSON = os.path.join(ROOT, 'analysis', 'district_taxes.json')

# 2025 mill levies (taxes billed in 2026), Assessor's "Mill Levy Changes from 2024 to 2025" file
LEVY = {'NFD': 18.565, 'NLD': 5.557, 'NLDB': 1.157, 'NEPD': 1.85, 'NED': 17.274, 'NEDDDA': 5.0}
SCHOOL_LEVY = 48.044   # Boulder Valley RE-2, same in every tax area here
# Districts in each tax area the sellers' accounts are in (same file, "Changes by Tax Area")
TAX_AREA = {'000166': ['NFD', 'NLD', 'NEPD'], '000167': ['NFD', 'NLD', 'NEPD'],
            '000160': ['NED', 'NFD', 'NLD', 'NEDDDA', 'NEPD'], '000161': ['NED', 'NFD', 'NLD', 'NEPD']}
# 2025 net total taxable assessed valuation, Assessor's December 2025 certification letters
CERT = {'NFD': 92_172_222, 'NLD': 115_647_370, 'NEPD': 115_997_775}
CERT_URL = 'https://assets.bouldercounty.gov/wp-content/uploads/2025/12/ar-certs-2025-{}.pdf'
LEVY_URL = 'https://assets.bouldercounty.gov/wp-content/uploads/2026/02/ar-milllevy-changes-2025.xlsx'
# Treasurer account pages, printed Oct. 27, 2026: 2025 assessed value and total tax billed in 2026
TREASURER = {'R0026875': (3_817_515, 374_353.16), 'P0401681': (672_715, 66_017.78), 'R0071874': (545_076, 53_451.26)}

CATEGORIES = [
    ('base', 'Base area: about 255 acres and its buildings', ['R0026875']),
    ('equip', 'Equipment and other business personal property at the base area', ['P0401681']),
    ('permit', 'Interest in about 480 acres of National Forest used under the Forest Service permit', ['R0071874']),
    ('other', 'Other ski-area land and improvements: the parking parcel, a 140-acre parcel, Lake Eldora lots, '
              'a mining claim, and small improvement accounts', None),
    ('ned', 'Three properties in Nederland, including Nederhaus', None),
]
# Left out: Lot 36 (R0512960), co-owned with private individuals; severed minerals (R0091743), held by another company
EXCLUDE = {'R0512960', 'R0091743'}


def build():
    accts = {r['strap']: r for r in csv.DictReader(open(os.path.join(PRIV, 'powdr_parcels.tsv')), delimiter='\t')}
    owner = {}
    for r in csv.DictReader(open(os.path.join(PRIV, 'Owner_Address.csv'), encoding='latin-1')):
        if r['strap'] in accts:
            owner.setdefault(r['strap'], r)
    vals = {r['strap']: r for r in csv.DictReader(open(os.path.join(PRIV, 'Values.csv'), encoding='latin-1'))
            if r['strap'] in accts and r['tax_yr'] == '2026'}

    def cat_of(s):
        g = accts[s]['group']
        return 'ned' if g == 'Nederland' else 'other'

    rows = {k: dict(key=k, label=lbl, accounts=[], av=0.0, tax=0.0, basis=set(), district={}) for k, lbl, _ in CATEGORIES}
    fixed = {s: k for k, _, ss in CATEGORIES if ss for s in ss}
    straps = sorted(set(accts) - EXCLUDE | {'P0401681'})
    for s in straps:
        k = fixed.get(s) or cat_of(s)
        area = '000167' if s == 'P0401681' else owner[s]['taxArea']
        if s in TREASURER:
            av, tax = TREASURER[s]
            av_school = av
            rows[k]['basis'].add('treasurer')
        else:
            v = vals[s]
            av, av_school = float(v['totalAssessedVal'] or 0), float(v['totalAssessedVal_School'] or 0)
            tax = av_school * SCHOOL_LEVY / 1000 + av * (float(owner[s]['mill_levy']) - SCHOOL_LEVY) / 1000
            rows[k]['basis'].add('calculated')
        r = rows[k]
        r['accounts'].append(s)
        r['av'] += av
        r['tax'] += tax
        for dname in TAX_AREA[area]:
            r['district'][dname] = r['district'].get(dname, 0) + av * LEVY[dname] / 1000
    cats = []
    for k, _, _ in CATEGORIES:
        r = rows[k]
        r['basis'] = sorted(r['basis'])
        r['n'] = len(r['accounts'])
        if k not in ('base', 'equip', 'permit'):
            r['accounts'] = []   # the page cites account numbers only for the three Treasurer bills
        cats.append(r)

    est = {}
    for dname in ('NFD', 'NLD', 'NEPD'):
        lo = sum(c['district'].get(dname, 0) for c in cats if c['key'] != 'permit')
        hi = lo + rows['permit']['district'].get(dname, 0)
        base = CERT[dname] * LEVY[dname] / 1000
        est[dname] = dict(levy=LEVY[dname], low=lo, high=hi, district_total=base, cert=CERT[dname],
                          share_low=lo / base, share_high=hi / base)
    nld_av = est['NLD']['low'] / LEVY['NLD'] * 1000
    est['NLD']['bond_part_low'] = nld_av * LEVY['NLDB'] / 1000
    est['NLD']['bond_part_high'] = (nld_av + rows['permit']['av']) * LEVY['NLDB'] / 1000
    data = dict(categories=cats, estimate=est, levy=LEVY, cert=CERT,
                total_av=sum(c['av'] for c in cats), total_tax=sum(c['tax'] for c in cats))
    json.dump(data, open(OUT_JSON, 'w'), indent=1)
    print(json.dumps({d: {k: round(v, 3) if isinstance(v, float) else v for k, v in x.items()} for d, x in est.items()}, indent=1))


def money(v):
    return f'${v:,.0f}'


def k(v):
    return f'about ${round(v, -3):,.0f}'


def rng(lo, hi):
    return f'about ${round(lo, -3):,.0f} to ${round(hi, -3):,.0f}'


def pct(v):
    return f'{v * 100:.1f}%'


def one(x):
    mid = (x['low'] + x['high']) / 2
    return f'${round(mid, -(len(str(int(mid))) - 2)):,.0f}'


def summary():
    """Figures the record page's summary and lede quote."""
    data = json.load(open(OUT_JSON))
    f, l = data['estimate']['NFD'], data['estimate']['NLD']
    return dict(dt_fire=rng(f['low'], f['high']).replace('about ', ''),
                dt_lib=rng(l['low'], l['high']).replace('about ', ''),
                dt_fire_pct=f'about {round((f["share_low"] + f["share_high"]) / 2 * 100)}%',
                dt_lib_pct=f'about {round((l["share_low"] + l["share_high"]) / 2 * 100)}%',
                dt_total=f'about ${round(data["total_tax"], -3):,.0f}',
                # one rounded figure for the lede: the range midpoint to two significant digits
                dt_fire_one=one(f), dt_lib_one=one(l))


def html():
    data = json.load(open(OUT_JSON))
    est = data['estimate']
    acct = lambda c: ', '.join(c['accounts'])
    crow = []
    for c in data['categories']:
        basis = ('Treasurer, taxes billed in 2026' if c['basis'] == ['treasurer'] else
                 f'Calculated from county records ({c["n"]} accounts)')
        ref = f' <span class="mono">{acct(c)}</span>' if c['accounts'] else ''
        crow.append(f'<tr><td>{c["label"]}{ref}</td><td class="amount">{money(c["av"])}</td>'
                    f'<td class="amount">{money(c["tax"])}</td><td>{basis}</td></tr>')
    crow.append(f'<tr class="bl-total"><td><strong>Total</strong></td><td class="amount">{money(data["total_av"])}</td>'
                f'<td class="amount">{money(data["total_tax"])}</td><td>All taxing authorities</td></tr>')
    names = {'NFD': ('Nederland Fire Protection District', '0624-nfd'),
             'NLD': ('Nederland Community Library District', '0819-nld'),
             'NEPD': ('Nederland EcoPass district', '0816-nepd')}
    drow = []
    for dname, (nm, cert) in names.items():
        x = est[dname]
        drow.append(f'<tr><td>{nm}</td><td class="amount">{x["levy"]:.3f}</td>'
                    f'<td class="amount">{rng(x["low"], x["high"])}</td>'
                    f'<td class="amount">{k(x["district_total"])}</td>'
                    f'<td class="amount">{pct(x["share_low"])} to {pct(x["share_high"])}</td>'
                    f'<td><a href="{CERT_URL.format(cert)}" target="_blank" rel="noopener">2025 certification</a></td></tr>')
    nld = est['NLD']
    return f'''
  <section id="district-taxes">
    <h2>Property taxes on the resort</h2>
    <p class="prose muted">What the Town said about the fire and library districts' property taxes, what county records show the sellers' property pays now, and an estimate of what those districts would stop collecting if the property became the Town's. Unlike the rest of this page, this section also uses Boulder County Assessor and Treasurer records.</p>

    <h3 id="district-taxes-town">What the Town said</h3>
    <p class="prose">FAQ 6.0 (April 2, 2026) asked, &ldquo;Will special districts like the library and fire department lose revenue because of the acquisition?&rdquo; It answered that property owned by a municipality &ldquo;is generally exempt from property taxation under Colorado law,&rdquo; so parcels that become Town-owned &ldquo;may no longer be subject to property taxes,&rdquo; and that taxes already assessed for the current year would not be affected. It said the Town was &ldquo;working directly with the County Assessor to identify which parcels, if any, would become Town-owned&rdquo; and would share what it learned &ldquo;through the Town's public channels&rdquo; (<a href="https://www.nederlandco.gov/m/newsflash/home/detail/22" target="_blank" rel="noopener">FAQ 6.0, Q26</a>). FAQ 7.0 (July 23, 2026) does not include the question, and no results of that review are in the records searched (<a href="#open-questions">Not in the records searched</a>).</p>

    <h3 id="district-taxes-now">What the sellers' property pays now</h3>
    <p class="prose">The purchase agreement names the sellers as POWDR Corp., Eldora Enterprises LLC, Mountain Lease Enterprises LLC, and Eldora Ski LLC, and defines the land being sold as all land &ldquo;owned by any Seller&rdquo; (<a href="https://nederlandco.civicweb.net/document/126803/" target="_blank" rel="noopener">APA, preamble and Art. 1</a>). The agreement's list of parcels, Schedule 5.7(a), isn't public. The table covers the accounts the county records under Eldora Enterprises and Mountain Lease Enterprises; it leaves out one lot co-owned with private individuals and mineral rights held by another company. The Treasurer bills the Forest Service permit interest under the name Lake Eldora Corp.</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">Property</th><th scope="col">Assessed value</th><th scope="col">Property tax</th><th scope="col">Basis</th></tr></thead>
      <tbody>{''.join(crow)}</tbody>
    </table></div>
    <p class="prose muted">Values are &ldquo;for assessment purposes only&rdquo; and are not market values or appraisals (Boulder County Treasurer). The three largest accounts are the Treasurer's bills on 2025 values. The other rows use the Assessor's 2026 values and 2025 tax rates; their 2025 values may be slightly higher. Anyone can look up an account by number on the <a href="https://treasurer.bouldercounty.org/treasurer/web/" target="_blank" rel="noopener">Treasurer's site</a>.</p>

    <h3 id="district-taxes-estimate">If the property became the Town's</h3>
    <p class="prose">The ski area is in county tax areas that include the Nederland Fire Protection District, the Nederland Community Library District, and the Nederland EcoPass district, along with Boulder County, RTD, and the Boulder Valley School District. The Nederland properties are also in the Town and, for one, the Downtown Development Authority (<a href="{LEVY_URL}" target="_blank" rel="noopener">county mill levy file</a>). If the property became tax-exempt Town property, each district would stop collecting the tax on it, estimated below at 2025 rates. The range depends on the Forest Service permit interest: it is taxed while a private company holds it, and whether it would be taxed if the Town held the permit is for the Assessor to decide.</p>
    <div class="scroll"><table class="commit">
      <thead><tr><th scope="col">District</th><th scope="col">Rate (mills, 2025)</th><th scope="col">Tax on the sellers' property each year</th><th scope="col">District's property tax on all taxable property</th><th scope="col">Share</th><th scope="col">Source</th></tr></thead>
      <tbody>{''.join(drow)}</tbody>
    </table></div>
    <ul class="notes prose">
      <li><strong>An estimate, not a ruling.</strong> Whether each account becomes exempt is for the County Assessor to decide. Town property leased to a private party can remain taxable. The estimate assumes the sale includes all the accounts in the table above.</li>
      <li><strong>Part of the library's rate repays bonds.</strong> The county lists a separate &ldquo;bond only&rdquo; rate of {LEVY['NLDB']:.3f} mills for the library district, and both rates fell by the same amount from 2024 to 2025, which suggests about {LEVY['NLDB']:.3f} of the library's {LEVY['NLD']:.3f} mills repays bonds. A bond levy is usually set each year to raise what is owed, so that part ({rng(nld['bond_part_low'], nld['bond_part_high'])}) would likely shift to other property owners rather than be lost. The library district or the county could confirm this.</li>
      <li><strong>Who would hold title.</strong> Under the sale-leaseback the Town described in October 2026, a bond trustee, not the Town, would hold legal title to the land and buildings until the bonds are repaid, and would lease the resort to the Town's enterprise (<a href="https://nederlandco.civicweb.net/document/132788/" target="_blank" rel="noopener">sale-leaseback overview</a>). Whether that affects the property's tax status is for the County Assessor to decide; if the property remained taxable, the districts would keep collecting these taxes. FAQ 6.0's answer predates the sale-leaseback.</li>
      <li><strong>Only after a closing.</strong> No sale has closed, and the Town said Sept. 30, 2026, that the purchase agreement &ldquo;has expired&rdquo; (<a href="#no-sale">If the sale doesn't go through</a>). Property taxes are billed a year in arrears, so any change would appear in tax bills a year or more after a closing.</li>
      <li><strong>Later years.</strong> The Assessor's 2026 values for the base area and the permit interest are lower than the 2025 values used here, so at the same rates the amounts for later years would be somewhat smaller. Districts can change their rates within what their voters have approved.</li>
    </ul>

  </section>
'''


if __name__ == '__main__':
    if '--build' in sys.argv:
        build()
    else:
        print(html())
