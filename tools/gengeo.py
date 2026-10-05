# -*- coding: utf-8 -*-
"""butterflies.json 의 날개 윤곽을 '실제 나비 모양'으로 다시 그립니다.
   한 종을 몇 개의 랜드마크(뿌리·날개끝·뒤귀퉁이)와 휘어짐 값으로 적고,
   거기서 베지어 윤곽·날개맥 방향점·물결 테두리를 자동으로 뽑습니다."""
import json, math, copy, sys, re

R = lambda v: round(v + 0.0, 3)

def seg(P, Q, t1, n1, t2, n2):
    """P→Q 로 가는 베지어 한 구간. t=진행 비율, n=진행 방향 왼쪽으로 밀어내는 양."""
    dx, dy = Q[0]-P[0], Q[1]-P[1]
    L = math.hypot(dx, dy) or 1e-6
    nx, ny = dy/L, -dx/L
    return [R(P[0]+dx*t1+nx*n1), R(P[1]+dy*t1+ny*n1),
            R(P[0]+dx*t2+nx*n2), R(P[1]+dy*t2+ny*n2), R(Q[0]), R(Q[1])]

def bez(p0, s, t):
    c1 = (s[0], s[1]); c2 = (s[2], s[3]); p1 = (s[4], s[5]); v = 1-t
    return (v*v*v*p0[0] + 3*v*v*t*c1[0] + 3*v*t*t*c2[0] + t*t*t*p1[0],
            v*v*v*p0[1] + 3*v*v*t*c1[1] + 3*v*t*t*c2[1] + t*t*t*p1[1])

def polyline(path, per=40):
    """[시작점, 구간…] → 조밀한 점열 (구간 경계 인덱스도 함께)"""
    pts = [tuple(path[0])]; bounds = [0]
    p0 = tuple(path[0])
    for s in path[1:]:
        for i in range(1, per+1):
            pts.append(bez(p0, s, i/per))
        bounds.append(len(pts)-1)
        p0 = (s[4], s[5])
    return pts, bounds

def sample(pts, i0, i1, n):
    """점열의 [i0,i1] 구간을 길이에 따라 n 등분해 뽑습니다 (날개맥이 고르게 퍼지도록)."""
    seg_pts = pts[i0:i1+1]
    cum = [0.0]
    for a, b in zip(seg_pts, seg_pts[1:]):
        cum.append(cum[-1] + math.hypot(b[0]-a[0], b[1]-a[1]))
    total = cum[-1] or 1e-6
    out = []
    for k in range(n):
        want = total * k / (n - 1)
        j = 0
        while j < len(cum)-2 and cum[j+1] < want: j += 1
        d = (cum[j+1]-cum[j]) or 1e-6
        t = (want - cum[j]) / d
        a, b = seg_pts[j], seg_pts[min(j+1, len(seg_pts)-1)]
        out.append([R(a[0] + (b[0]-a[0])*t), R(a[1] + (b[1]-a[1])*t)])
    return out

# ── 앞날개 ────────────────────────────────────────────────────
# base  : 몸통에 붙는 위쪽 점        apex : 날개 끝
# tornus: 바깥 가장자리의 아래 귀퉁이  costa/termen/dorsum : 각 변의 휘어짐
def forewing(p):
    B = [0.0, p["base"]]; A = p["apex"]; T = p["tornus"]; D = [0.01, 0.01]
    c = p.get("costa", (0.14, 0.11)); t = p.get("termen", (0.0, 0.0)); d = p.get("dorsum", 0.03)
    cut = p.get("apexCut", 0.0)      # 날개끝을 바늘처럼 뾰족하지 않게 — 짧게 잘라 줍니다
    if cut > 0:
        ux, uy = A[0]-B[0], A[1]-B[1]; L = math.hypot(ux, uy) or 1e-6
        A1 = [A[0]-ux/L*cut, A[1]-uy/L*cut]
        vx, vy = T[0]-A[0], T[1]-A[1]; M = math.hypot(vx, vy) or 1e-6
        A2 = [A[0]+vx/M*cut, A[1]+vy/M*cut]
        path = [B,
                seg(B, A1, 0.34, c[0], 0.74, c[1]),
                seg(A1, A2, 0.30, cut*0.45, 0.70, cut*0.45),    # 모서리를 둥글게
                seg(A2, T, 0.30, t[0], 0.72, t[1]),
                seg(T, D, 0.35, d,   0.72, d*0.55)]
    else:
        path = [B,
                seg(B, A, 0.34, c[0], 0.74, c[1]),
                seg(A, T, 0.30, t[0], 0.72, t[1]),
                seg(T, D, 0.35, d,   0.72, d*0.55)]
    pts, bd = polyline(path)
    # 날개맥은 앞가장자리 바깥쪽 1/3 → 날개끝 → 바깥가장자리 → 뒤귀퉁이까지 퍼집니다
    last = len(bd) - 1
    i0 = bd[0] + int((bd[1]-bd[0]) * p.get("edge0", 0.56))
    i1 = bd[last-1] + int((bd[last]-bd[last-1]) * p.get("edge1", 0.20))
    return path, sample(pts, i0, i1, 8)

# ── 뒷날개 ────────────────────────────────────────────────────
# top : 앞날개 밑에 숨는 위쪽 뿌리   out : 바깥으로 가장 멀리 나간 점
# anal: 아래쪽 귀퉁이                lead/outer/inner : 각 변의 휘어짐
def hindwing(p):
    B = [0.01, p.get("top", -0.02)]; O = p["out"]; N = p["anal"]; D = [0.0, p.get("foot", 0.10)]
    l = p.get("lead", (0.03, 0.05)); o = p.get("outer", (0.05, 0.05)); i = p.get("inner", -0.02)
    path = [B,
            seg(B, O, 0.38, l[0], 0.76, l[1]),
            seg(O, N, 0.28, o[0], 0.70, o[1]),
            seg(N, D, 0.34, i,   0.70, i*0.6)]
    pts, bd = polyline(path)
    i0 = bd[0] + int((bd[1]-bd[0]) * p.get("edge0", 0.52))
    i1 = bd[2] + int((bd[3]-bd[2]) * p.get("edge1", 0.18))
    return path, sample(pts, i0, i1, 7), (pts, bd)

# ── 꼬리 ──────────────────────────────────────────────────────
def tail_on_margin(hpts, hbd, t, length, wb, wt, swing=0.0, sink=0.12, flare=0.75):
    """뒷날개 바깥 가장자리의 t 지점(0=바깥 끝, 1=아래 모서리)에서 꼬리를 뽑습니다.
       뿌리에서 바깥으로 향하는 방향을 그대로 따라가므로 꼬리는 늘 날개에 붙어 있고,
       sink 만큼 날개 안쪽에 파묻혀 뿌리가 날개와 한 덩어리로 이어집니다."""
    seg_pts = hpts[hbd[1]:hbd[2]+1]
    P = seg_pts[max(0, min(len(seg_pts)-1, int(round(t*(len(seg_pts)-1)))))]
    L = math.hypot(P[0], P[1]) or 1e-6
    ux, uy = P[0]/L, P[1]/L
    ca, sa = math.cos(swing), math.sin(swing)
    vx, vy = ux*ca - uy*sa, ux*sa + uy*ca
    att = [P[0] - ux*sink, P[1] - uy*sink]
    tip = [att[0] + vx*length, att[1] + vy*length]
    # 테두리는 뿌리 쪽에서 날개와 같은 두께로 붙어 있다가, 꼬리가 날개를 완전히
    # 벗어난 뒤 짧은 구간에서 가늘어집니다. 천천히 바꾸면 반투명한 얼룩이 됩니다.
    p0 = [att[0] + vx*length*0.46, att[1] + vy*length*0.46]
    p1 = [att[0] + vx*length*0.62, att[1] + vy*length*0.62]
    return tailshape(att, tip, wb, wt, flare), \
           { "from": [R(p0[0]), R(p0[1])], "to": [R(p1[0]), R(p1[1])] }

def tailshape(att, tip, wb, wt, flare=0.75):
    """뿌리는 넓게 벌어지고 금세 가늘어졌다가 거의 나란히 뻗는 제비꼬리 모양.
       옆선을 안쪽으로 오목하게 당겨야 날개에서 자라난 것처럼 보입니다."""
    ax, ay = att; tx, ty = tip
    dx, dy = tx-ax, ty-ay; L = math.hypot(dx, dy) or 1e-6
    nx, ny = dy/L, -dx/L
    A1 = [ax+nx*wb, ay+ny*wb]; A2 = [ax-nx*wb, ay-ny*wb]
    T1 = [tx+nx*wt, ty+ny*wt]; T2 = [tx-nx*wt, ty-ny*wt]
    k = max(0.0, wb - wt)
    return [[R(A1[0]), R(A1[1])],
            seg(A1, T1, 0.26, -k*flare, 0.68, -k*0.16),
            seg(T1, T2, 0.30, -wt*0.9, 0.70, -wt*0.9),
            seg(T2, A2, 0.32, -k*0.16, 0.74, -k*flare),
            seg(A2, A1, 0.5, 0, 0.5, 0)]

SPECIES = {
 # ── 모르포: 아주 넓고 둥글다. 날개끝이 살짝 낫처럼 빠지고 바깥 가장자리가 옅게 패인다.
 "morpho": dict(
   fore=dict(base=-0.10, apex=[0.99,-0.60], tornus=[0.78,0.07],
             costa=(0.175,0.10), termen=(0.025,-0.025), dorsum=0.035, apexCut=0.055, edge0=0.54, edge1=0.20),
   hind=dict(top=-0.03, out=[0.80,0.34], anal=[0.33,0.78], foot=0.11,
             lead=(0.13,0.17), outer=(0.19,0.18), inner=-0.03, edge0=0.46),
   scallop=dict(hind=dict(n=7, d=0.018, **{"from":0.76}))),

 # ── 호랑나비: 길쭉한 삼각 앞날개 + 물결치는 뒷날개 + 주걱 꼬리.
 "xuthus": dict(
   fore=dict(base=-0.11, apex=[1.14,-0.65], tornus=[0.70,0.07],
             costa=(0.16,0.09), termen=(0.055,0.035), dorsum=0.03, apexCut=0.045, edge0=0.58, edge1=0.20),
   hind=dict(top=-0.03, out=[0.72,0.33], anal=[0.31,0.75], foot=0.10,
             lead=(0.11,0.145), outer=(0.15,0.145), inner=-0.03, edge0=0.44),
   tail=dict(at=0.62, len=0.46, wb=0.062, wt=0.044, swing=-0.14, sink=0.145, flare=0.62, band=0.030),
   scallop=dict(hind=dict(n=6, d=0.024, **{"from":0.60}),
                fore=dict(n=5, d=0.010, **{"from":0.82}))),

 # ── 모나크: 길고 끝이 모난 앞날개, 바깥 가장자리가 안으로 패임. 뒷날개는 작고 둥글다.
 "monarch": dict(
   fore=dict(base=-0.09, apex=[1.14,-0.68], tornus=[0.68,0.06],
             costa=(0.16,0.085), termen=(0.01,-0.065), dorsum=0.028, apexCut=0.06, edge0=0.58, edge1=0.20),
   hind=dict(top=-0.03, out=[0.64,0.31], anal=[0.28,0.64], foot=0.09,
             lead=(0.10,0.135), outer=(0.155,0.15), inner=-0.025, edge0=0.46),
   scallop=dict(hind=dict(n=6, d=0.013, **{"from":0.78}))),

 # ── 배추흰나비: 작고 동글동글. 앞날개 끝이 둥글다.
 "rapae": dict(
   fore=dict(base=-0.09, apex=[0.96,-0.56], tornus=[0.66,0.07],
             costa=(0.175,0.115), termen=(0.075,0.055), dorsum=0.03, apexCut=0.07, edge0=0.50, edge1=0.22),
   hind=dict(top=-0.03, out=[0.68,0.35], anal=[0.29,0.66], foot=0.09,
             lead=(0.13,0.165), outer=(0.175,0.17), inner=-0.02, edge0=0.46)),

 # ── 녹색부전나비: 작은 삼각 앞날개 + 뒷날개 아래 모서리에서 나온 실꼬리.
 "hairstreak": dict(
   fore=dict(base=-0.09, apex=[0.92,-0.54], tornus=[0.62,0.06],
             costa=(0.155,0.09), termen=(0.05,0.04), dorsum=0.026, apexCut=0.05, edge0=0.54, edge1=0.20),
   hind=dict(top=-0.03, out=[0.62,0.33], anal=[0.27,0.62], foot=0.09,
             lead=(0.11,0.14), outer=(0.15,0.145), inner=-0.02, edge0=0.46),
   tail=dict(at=0.90, len=0.30, wb=0.060, wt=0.014, swing=-0.05, sink=0.11, flare=0.86, band=0.009)),

 # ── 유리날개나비: 길쭉하고 끝이 둥근 앞날개.
 "glasswing": dict(
   fore=dict(base=-0.09, apex=[1.06,-0.58], tornus=[0.64,0.06],
             costa=(0.165,0.10), termen=(0.07,0.05), dorsum=0.026, apexCut=0.065, edge0=0.54, edge1=0.20),
   hind=dict(top=-0.03, out=[0.66,0.35], anal=[0.28,0.66], foot=0.09,
             lead=(0.115,0.15), outer=(0.165,0.16), inner=-0.02, edge0=0.46)),

 # ── 얼룩말긴날개나비: 앞날개가 유난히 길고 좁다. 뒷날개는 작은 타원.
 "zebra": dict(
   fore=dict(base=-0.07, apex=[1.30,-0.56], tornus=[0.72,0.05],
             costa=(0.175,0.075), termen=(0.06,0.055), dorsum=0.022, apexCut=0.09, edge0=0.60, edge1=0.18),
   hind=dict(top=-0.02, out=[0.68,0.34], anal=[0.28,0.70], foot=0.09,
             lead=(0.14,0.175), outer=(0.155,0.15), inner=-0.015, edge0=0.46)),

 # ── 공작나비: 날개끝이 뾰족 튀어나오고 그 아래가 움푹. 테두리가 가장 우글우글하다.
 "peacock": dict(
   fore=dict(base=-0.10, apex=[1.05,-0.645], tornus=[0.70,0.07],
             costa=(0.175,0.085), termen=(0.02,-0.075), dorsum=0.03, apexCut=0.07, edge0=0.56, edge1=0.20),
   hind=dict(top=-0.03, out=[0.74,0.35], anal=[0.31,0.72], foot=0.10,
             lead=(0.12,0.155), outer=(0.16,0.155), inner=-0.03, edge0=0.44),
   scallop=dict(fore=dict(n=5, d=0.030, **{"from":0.64}),
                hind=dict(n=7, d=0.038, **{"from":0.56}))),

 # ── 붉은제독: 날개끝이 네모지게 튀어나오고 아래가 패임. 뒷날개 테두리는 잔물결.
 "admiral": dict(
   fore=dict(base=-0.10, apex=[1.04,-0.61], tornus=[0.68,0.07],
             costa=(0.16,0.09), termen=(0.01,-0.035), dorsum=0.03, apexCut=0.06, edge0=0.56, edge1=0.20),
   hind=dict(top=-0.03, out=[0.70,0.34], anal=[0.30,0.68], foot=0.09,
             lead=(0.12,0.155), outer=(0.16,0.155), inner=-0.025, edge0=0.46),
   scallop=dict(fore=dict(n=4, d=0.016, **{"from":0.78}),
                hind=dict(n=8, d=0.024, **{"from":0.66}))),

 # ── 올빼미나비: 가장 크고 넓다. 앞날개 바깥이 깊게 패이고 뒷날개는 둥근 부채.
 "owl": dict(
   fore=dict(base=-0.11, apex=[1.02,-0.60], tornus=[0.82,0.08],
             costa=(0.19,0.11), termen=(0.02,-0.06), dorsum=0.035, apexCut=0.065, edge0=0.50, edge1=0.20),
   hind=dict(top=-0.03, out=[0.86,0.36], anal=[0.35,0.82], foot=0.11,
             lead=(0.145,0.185), outer=(0.205,0.195), inner=-0.03, edge0=0.44),
   scallop=dict(hind=dict(n=8, d=0.014, **{"from":0.80}))),

 # ── 알렉산드라비단제비나비: 아주 길고 뾰족한 앞날개, 각진 뒷날개.
 "birdwing": dict(
   fore=dict(base=-0.11, apex=[1.28,-0.72], tornus=[0.68,0.06],
             costa=(0.15,0.075), termen=(0.035,0.015), dorsum=0.026, apexCut=0.05, edge0=0.60, edge1=0.18),
   hind=dict(top=-0.03, out=[0.72,0.35], anal=[0.31,0.68], foot=0.10,
             lead=(0.10,0.13), outer=(0.135,0.13), inner=-0.025, edge0=0.46)),
}

def tidy(txt):
    """숫자만 든 배열은 한 줄로 모읍니다 — 손으로 고치기 좋게."""
    num = re.compile(r"\[\s*(-?\d[\d.eE+-]*)(?:,\s*(-?\d[\d.eE+-]*))*\s*\]", re.S)
    def flat(m):
        return "[" + ", ".join(t.strip() for t in m.group(0).strip("[]").replace("\n", " ").split(",")) + "]"
    txt = num.sub(flat, txt)
    grp = re.compile(r"\[\s*(\[[^\[\]]*\])(?:,\s*(\[[^\[\]]*\]))*\s*\]", re.S)
    def flat2(m):
        inner = re.findall(r"\[[^\[\]]*\]", m.group(0))
        return "[" + ", ".join(inner) + "]"
    return grp.sub(flat2, txt)

def main(src, dst):
    data = json.load(open(src, encoding="utf-8"))
    for rec in data["species"]:
        p = SPECIES.get(rec["id"])
        if not p: continue
        r = rec["render"]
        fpath, fedge = forewing(p["fore"])
        hpath, hedge, (hpts, hbd) = hindwing(p["hind"])
        r["fore"] = fpath; r["foreEdge"] = fedge
        r["hind"] = hpath; r["hindEdge"] = hedge
        if "tail" in p:
            t = p["tail"]
            r["tail"], axis = tail_on_margin(hpts, hbd, t["at"], t["len"], t["wb"], t["wt"],
                                       t.get("swing", 0.0), t.get("sink", 0.12), t.get("flare", 0.75))
            r["band"]["tail"] = t["band"]
        else:
            r.pop("tail", None)
            r["band"].pop("tail", None)
        if "scallop" in p: r["scallop"] = p["scallop"]
        else: r.pop("scallop", None)
    data["renderFields"]["band"] = (
        "{ fore, hind, tail } — 검은 테두리 폭. 0.016(거의 없음) ~ 0.06(모나크처럼 넓음). "
        "꼬리가 있는 종은 꼬리와 뒷날개의 테두리가 이음매 없이 이어지고, tail 값이 꼬리 쪽 폭입니다.")
    data["renderFields"]["scallop"] = (
        "{ fore, hind } — 바깥 가장자리의 물결(거치). 각각 { n: 물결 개수, d: 깊이(날개폭 비율), "
        "from: 물결이 시작되는 거리 비율 }. 네발나비과(공작·제독)처럼 테두리가 우글우글한 종에 씁니다. "
        "없으면 가장자리가 매끈합니다.")
    txt = json.dumps(data, ensure_ascii=False, indent=2)
    txt = tidy(txt)
    open(dst, "w", encoding="utf-8").write(txt + "\n")
    print("wrote", dst)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
