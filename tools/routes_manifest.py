"""路线清单：途经点 + 元数据。build_tracks.py 据此生成真实轨迹。

waypoints 顺序即行进顺序，坐标可写近似值：
- 普通点位（庙宇、村寨、观景台）：OSRM 会自动吸附到最近步道；
- 山顶：加 snap="peak"，构建时用 SRTM 海拔网格自动校正到真正的最高点，
  避免人工填坐标偏一两公里。
"""

P = lambda name, lat, lon, **kw: dict(name=name, lat=lat, lon=lon, **kw)  # noqa: E731
PEAK = lambda name, lat, lon, r=0.03: dict(name=name, lat=lat, lon=lon, snap="peak", r=r)  # noqa: E731


ROUTES = [
    # ============================================================ 湖南
    dict(
        id="hn-hengyang-zhurong",
        name="南岳衡山·祝融峰登山古道",
        province="湖南省", city="衡阳市", type="山岳古道",
        difficulty="中等", days="1天", best_season="3-11月", heat=88,
        desc="从南岳大庙经忠烈祠、半山亭一路石阶上祝融峰，香客与徒步者同路，"
             "沿途补给点密集。祝融峰海拔 1289 米，是南岳七十二峰最高点，"
             "秋冬云海和雾凇各有一批固定粉丝。",
        waypoints=[
            P("南岳大庙", 27.2419, 112.7341),
            P("忠烈祠", 27.2515, 112.7295),
            P("华严湖", 27.2610, 112.7230),
            P("半山亭", 27.2705, 112.7150),
            P("南天门", 27.2855, 112.7005),
            PEAK("祝融峰", 27.2950, 112.6970),
        ],
    ),
    dict(
        id="hn-zhangjiajie-jinbianxi",
        name="张家界·金鞭溪—袁家界环线",
        province="湖南省", city="张家界市", type="峡谷森林",
        difficulty="中等", days="1-2天", best_season="4-10月", heat=92,
        desc="金鞭溪沿溪谷平缓，两岸石峰夹峙，走到水绕四门后上袁家界看"
             "「哈利路亚山」原型乾坤柱。溪谷阴凉、石英砂岩峰林密集，"
             "是武陵源最不需要体力又能看足景的一段。",
        waypoints=[
            P("森林公园门票站", 29.3179, 110.4341),
            P("金鞭溪", 29.3288, 110.4372),
            P("紫草潭", 29.3405, 110.4402),
            P("水绕四门", 29.3483, 110.4436),
            P("百龙天梯", 29.3560, 110.4710),
            P("袁家界", 29.3606, 110.4778),
            P("天下第一桥", 29.3636, 110.4800),
        ],
    ),
    dict(
        id="hn-zhangjiajie-tianmenshan",
        name="张家界·天门山天梯栈道",
        province="湖南省", city="张家界市", type="山岳栈道",
        difficulty="中等", days="1天", best_season="4-11月", heat=90,
        desc="999 级天梯直上天门洞，玻璃栈道贴崖而行；恐高者建议只走天梯段。"
             "洞口到山顶还有鬼谷栈道一段，绕崖一圈，脚下就是垂直几百米的崖壁。",
        waypoints=[
            P("天门山山门", 29.0470, 110.4760),
            P("上天梯下", 29.0510, 110.4770),
            P("天门洞", 29.0535, 110.4780),
            P("鬼谷栈道", 29.0620, 110.4800),
            PEAK("天门山顶", 29.0680, 110.4810, r=0.02),
        ],
    ),
    dict(
        id="hn-shaoyang-langshan",
        name="崀山·八角寨丹霞环线",
        province="湖南省", city="邵阳市", type="丹霞地貌",
        difficulty="中等", days="1天", best_season="3-11月", heat=76,
        desc="八角寨是崀山最出片的一处，站在寨顶看四周圆锥状丹霞峰丛，"
             "晨雾起时像浮在海上的石笋群。石阶连续上升，中途有云台寺可歇脚。",
        waypoints=[
            P("窑市（崀山景区入口）", 26.4020, 110.8420),
            P("八角寨山门", 26.4200, 110.8120),
            P("云台寺", 26.4270, 110.8160),
            PEAK("八角寨顶", 26.4310, 110.8180, r=0.02),
        ],
    ),
    dict(
        id="hn-chenzhou-mangshan",
        name="莽山·五指峰",
        province="湖南省", city="郴州市", type="原始森林",
        difficulty="较难", days="1-2天", best_season="5-10月", heat=74,
        desc="南岭腹地原始次生林，夏季凉爽；山路多苔藓湿滑，建议带登山杖。"
             "五指峰一线看点是华南五针松和垂直崖壁，秋冬常见云海灌满山谷。",
        waypoints=[
            P("莽山国家森林公园大门", 24.9500, 112.9200),
            P("鬼子寨", 24.9700, 112.9400),
            PEAK("五指峰", 24.9900, 112.9600),
        ],
    ),
    dict(
        id="hn-changsha-daweishan",
        name="大围山·七星岭",
        province="湖南省", city="长沙市", type="山岳森林",
        difficulty="中等", days="1天", best_season="4-11月", heat=72,
        desc="长沙周边最像样的山，七星岭海拔 1607 米，是湘东第一高峰。"
             "四月杜鹃、十月红叶，山顶风大，夏天也要带件外套。",
        waypoints=[
            P("大围山镇", 28.3900, 114.0500),
            P("栗木桥", 28.4100, 114.0700),
            PEAK("七星岭", 28.4250, 114.0800),
        ],
    ),
    dict(
        id="hn-yueyang-mufushan",
        name="幕阜山",
        province="湖南省", city="岳阳市", type="山岳",
        difficulty="较易", days="1天", best_season="4-10月", heat=62,
        desc="湘鄂赣三省交界的幕阜山脉主峰，海拔 1596 米，山脊线开阔，"
             "可一眼望三省。上山路以盘山公路加石阶为主，体力要求不算高。",
        waypoints=[
            P("幕阜山入口", 28.9600, 113.7500),
            P("半山", 28.9700, 113.7700),
            PEAK("主峰", 28.9800, 113.7800),
        ],
    ),
    dict(
        id="hn-changde-hupingshan",
        name="壶瓶山",
        province="湖南省", city="常德市", type="原始森林",
        difficulty="较难", days="2天", best_season="5-10月", heat=66,
        desc="湖南屋脊，主峰 2099 米。象鼻子沟一段溪谷原始，需要涉水与攀石，"
             "建议两天走完并在山上过夜；雨季溪水暴涨风险高，务必查天气。",
        waypoints=[
            P("壶瓶山镇", 29.9800, 110.6000),
            P("象鼻子沟", 30.0100, 110.6200),
            PEAK("壶瓶山主峰", 30.0300, 110.6300),
        ],
    ),
    dict(
        id="hn-zhangjiajie-badagongshan",
        name="八大公山",
        province="湖南省", city="张家界市", type="原始森林",
        difficulty="较难", days="2天", best_season="5-10月", heat=60,
        desc="国家级自然保护区，亚热带常绿阔叶林保存完整，人少、路野、"
             "信号弱。天平山一线是主要徒步走廊，需提前报备进入。",
        waypoints=[
            P("八大公山管理站", 29.6000, 109.9500),
            P("天平山", 29.6200, 109.9800),
            PEAK("主峰", 29.6350, 110.0000),
        ],
    ),
    dict(
        id="hn-yongzhou-yangmingshan",
        name="阳明山",
        province="湖南省", city="永州市", type="山岳花海",
        difficulty="较易", days="1天", best_season="4-11月", heat=68,
        desc="四月十万亩野生杜鹃是招牌，其余月份胜在人少清静。"
             "万寿寺到望佛台一段石阶连续，坡度不算陡，适合带家人。",
        waypoints=[
            P("阳明山大门", 25.9900, 111.9000),
            P("万寿寺", 26.0100, 111.9200),
            PEAK("望佛台", 26.0300, 111.9350),
        ],
    ),
    dict(
        id="hn-yongzhou-shunhuangshan",
        name="舜皇山",
        province="湖南省", city="永州市", type="山岳森林",
        difficulty="中等", days="1天", best_season="4-11月", heat=58,
        desc="舜帝南巡驻跸之地，主峰 1882 米。林下溪涧多，夏季比市区低五六度；"
             "后半程山脊无遮挡，注意防晒与补水。",
        waypoints=[
            P("舜皇山入口", 26.3500, 111.2600),
            P("半山亭", 26.3700, 111.2750),
            PEAK("舜皇山主峰", 26.3900, 111.2900),
        ],
    ),
    dict(
        id="hn-huaihua-xuefengshan",
        name="雪峰山·苏宝顶",
        province="湖南省", city="怀化市", type="山岳",
        difficulty="较难", days="1-2天", best_season="5-10月", heat=63,
        desc="雪峰山主峰苏宝顶海拔 1934 米，抗战湘西会战旧战场就在这一带。"
             "山脊多雾，能见度变化快，建议带轨迹设备。",
        waypoints=[
            P("苏宝顶村", 27.2800, 110.2800),
            P("山脊", 27.2950, 110.2950),
            PEAK("苏宝顶", 27.3100, 110.3100),
        ],
    ),
    dict(
        id="hn-shaoyang-yunshan",
        name="云山",
        province="湖南省", city="邵阳市", type="山岳",
        difficulty="中等", days="1天", best_season="3-11月", heat=55,
        desc="武冈云山，主峰 1372 米，道教七十二福地之一。"
             "云山寺以上路段林密，夏天走起来阴凉，山顶常年有云。",
        waypoints=[
            P("云山脚下", 26.6600, 110.6600),
            P("云山寺", 26.6750, 110.6750),
            PEAK("云山主峰", 26.6900, 110.6900),
        ],
    ),
    dict(
        id="hn-changsha-yuelushan",
        name="岳麓山—橘子洲城市徒步",
        province="湖南省", city="长沙市", type="城市徒步",
        difficulty="入门", days="1天", best_season="全年", heat=85,
        desc="长沙最经典的城市徒步线：湖南大学出发，过岳麓书院、爱晚亭、麓山寺、"
             "云麓宫上到山顶观景台，再下到江边走到橘子洲头。"
             "全程有路灯和补给，晚上八点前都有人在走。",
        waypoints=[
            P("湖南大学", 28.1796, 112.9465),
            P("岳麓书院", 28.1838, 112.9412),
            P("爱晚亭", 28.1868, 112.9355),
            P("麓山寺", 28.1900, 112.9322),
            P("云麓宫", 28.1905, 112.9305),
            PEAK("岳麓山顶", 28.1895, 112.9290, r=0.008),
            P("橘子洲头", 28.1920, 112.9620),
        ],
    ),
    dict(
        id="hn-changde-taohuayuan",
        name="桃花源—夷望溪",
        province="湖南省", city="常德市", type="乡村田园",
        difficulty="较易", days="1天", best_season="3-11月", heat=65,
        desc="沿沅江支流走的田园线路，桃花山一段是《桃花源记》原型地，"
             "三月桃花、四月油菜。路面以田埂和村道为主，几乎无爬升。",
        waypoints=[
            P("桃花源古镇", 28.8950, 111.4750),
            P("桃花山", 28.9050, 111.4800),
            P("夷望溪渡口", 28.9200, 111.4900),
        ],
    ),
    # ============================================================ 广东
    dict(
        id="gd-shaoguan-danxiashan",
        name="丹霞山·长老峰—阳元石",
        province="广东省", city="韶关市", type="丹霞地貌",
        difficulty="中等", days="1-2天", best_season="3-12月", heat=86,
        desc="世界丹霞地貌命名地。长老峰看日出，阳元石看造型，中间隔锦江。"
             "长老峰一段石阶陡且窄，节假日排队明显，建议六点前进山。",
        waypoints=[
            P("丹霞山山门", 25.0150, 113.7450),
            PEAK("长老峰", 25.0250, 113.7470, r=0.012),
            P("翔龙湖", 25.0330, 113.7420),
            P("阳元石", 25.0335, 113.7395),
        ],
    ),
    dict(
        id="gd-huizhou-luofushan",
        name="罗浮山·飞云顶",
        province="广东省", city="惠州市", type="山岳",
        difficulty="较难", days="1天", best_season="3-11月", heat=79,
        desc="岭南道教名山，飞云顶海拔 1281 米，是惠州最高点。"
             "从冲虚古观起步一路爬升近千米，后半程石阶密集，膝盖负担大。",
        waypoints=[
            P("罗浮山朱明洞", 23.2650, 114.0550),
            P("冲虚古观", 23.2700, 114.0560),
            PEAK("飞云顶", 23.2820, 114.0620),
        ],
    ),
    dict(
        id="gd-shenzhen-wutongshan",
        name="梧桐山·大梧桐",
        province="广东省", city="深圳市", type="山岳",
        difficulty="中等", days="1天", best_season="10-4月", heat=84,
        desc="深圳最高峰，海拔 943 米。泰山涧一路上到山顶，能同时看到深圳市区、"
             "香港新界和大鹏湾。夏天中午暴晒，建议清晨出发。",
        waypoints=[
            P("梧桐山村", 22.5960, 114.2005),
            P("泰山涧", 22.5900, 114.2080),
            PEAK("大梧桐顶", 22.5820, 114.2200, r=0.012),
        ],
    ),
    dict(
        id="gd-shenzhen-qiniangshan",
        name="七娘山",
        province="广东省", city="深圳市", type="山岳海岸",
        difficulty="较难", days="1天", best_season="10-4月", heat=71,
        desc="深圳第二高峰，海拔 869 米，山体直插大亚湾。"
             "上山多为土路与碎石坡，下撤有陡崖段，雨天不建议前往。",
        waypoints=[
            P("七娘山登山口", 22.5400, 114.5480),
            PEAK("七娘山顶", 22.5520, 114.5560),
        ],
    ),
    dict(
        id="gd-shenzhen-dongxichong",
        name="东西冲海岸线穿越",
        province="广东省", city="深圳市", type="海岸线",
        difficulty="中等", days="1天", best_season="10-5月", heat=87,
        desc="深圳最著名的海岸线穿越，东冲进西冲出，全程礁石、沙滩、崖壁交替。"
             "涨潮时部分路段需绕行山腰，务必查潮汐表，不要单独前往。",
        waypoints=[
            P("东冲村", 22.4850, 114.5350),
            P("穿鼻岩", 22.4790, 114.5250),
            P("西冲沙滩", 22.4720, 114.5150),
        ],
    ),
    dict(
        id="gd-shaoguan-chuanding",
        name="船底顶",
        province="广东省", city="韶关市", type="山岳",
        difficulty="难", days="2天", best_season="10-4月", heat=75,
        desc="广东驴友口中的「船底顶」，海拔 1586 米，是省内强度标杆之一。"
             "罗坑上、上斜下，草坡与碎石坡混合，需要重装过夜，不适合新手。",
        waypoints=[
            P("罗坑镇", 24.4200, 113.0300),
            P("上斜村", 24.4400, 113.0450),
            PEAK("船底顶", 24.4520, 113.0520),
        ],
    ),
    dict(
        id="gd-guangzhou-baiyunshan",
        name="白云山",
        province="广东省", city="广州市", type="城市山岳",
        difficulty="入门", days="1天", best_season="全年", heat=82,
        desc="广州市区里的山，摩星岭海拔 382 米。云台花园进、山顶公园出，"
             "全程柏油与石阶，早晚都是跑步和遛弯的人，适合零基础。",
        waypoints=[
            P("云台花园", 23.1600, 113.3000),
            P("蒲谷", 23.1700, 113.3020),
            PEAK("摩星岭", 23.1800, 113.3050, r=0.01),
            P("山顶公园", 23.1780, 113.3030),
        ],
    ),
    dict(
        id="gd-qingyuan-yingxi",
        name="英西峰林走廊",
        province="广东省", city="清远市", type="喀斯特",
        difficulty="较易", days="1-2天", best_season="3-11月", heat=73,
        desc="「广东小桂林」，喀斯特峰丛间穿村道走，几乎无爬升。"
             "九龙镇到黄花镇一段最集中，适合轻装慢走、拍照。",
        waypoints=[
            P("九龙镇", 24.0300, 112.9400),
            P("洞天仙境", 24.0200, 112.9500),
            P("黄花镇", 24.0000, 112.9700),
        ],
    ),
    dict(
        id="gd-zhaoqing-dinghushan",
        name="鼎湖山",
        province="广东省", city="肇庆市", type="山岳森林",
        difficulty="较易", days="1天", best_season="3-11月", heat=78,
        desc="北回归线上的绿洲，庆云寺、飞水潭一线溪涧不断，"
             "负氧离子浓度常年偏高。主峰鸡笼山一带游客少，可加走。",
        waypoints=[
            P("鼎湖山门", 23.1600, 112.5300),
            P("庆云寺", 23.1680, 112.5330),
            P("飞水潭", 23.1700, 112.5350),
            PEAK("鸡笼山", 23.1750, 112.5380, r=0.012),
        ],
    ),
    dict(
        id="gd-foshan-xiaoshan",
        name="西樵山",
        province="广东省", city="佛山市", type="山岳",
        difficulty="入门", days="1天", best_season="全年", heat=74,
        desc="珠江三角洲唯一的古火山，大科峰海拔 344 米。"
             "北门进、天湖过、大科峰出，路面成熟，适合带老人小孩。",
        waypoints=[
            P("西樵山北门", 22.9400, 112.9700),
            P("天湖", 22.9330, 112.9730),
            PEAK("大科峰", 22.9280, 112.9700, r=0.01),
        ],
    ),
    dict(
        id="gd-shaoguan-shikengkong",
        name="南岭·石坑崆",
        province="广东省", city="韶关市", type="山岳",
        difficulty="难", days="2天", best_season="5-10月", heat=69,
        desc="广东最高峰，海拔 1902 米，也是南岭山脉主峰。"
             "小黄山一段有华南铁杉与高山草甸，山顶昼夜温差大，需带保暖层。",
        waypoints=[
            P("南岭国家森林公园", 24.8900, 112.9500),
            P("小黄山", 24.9100, 112.9650),
            PEAK("石坑崆", 24.9200, 112.9800),
        ],
    ),
    dict(
        id="gd-huizhou-heipaijiao",
        name="黑排角海岸线",
        province="广东省", city="惠州市", type="海岸线",
        difficulty="中等", days="1天", best_season="10-5月", heat=72,
        desc="惠东稔山一带的礁石海岸，黑色玄武岩被浪切成片状，"
             "退潮时能走出很远。部分路段需手脚并用，防滑鞋必备。",
        waypoints=[
            P("稔山", 22.7600, 114.8300),
            P("黑排角", 22.7500, 114.8500),
            P("盐洲岛", 22.7400, 114.8700),
        ],
    ),
    dict(
        id="gd-shenzhen-dapeng-geopark",
        name="大鹏半岛国家地质公园",
        province="广东省", city="深圳市", type="地质海岸",
        difficulty="较易", days="1天", best_season="10-4月", heat=70,
        desc="火山岩与海岸地貌的教科书现场，鹿嘴到杨梅坑一段海崖连续。"
             "路面以栈道和村道为主，适合半天轻徒步加拍照。",
        waypoints=[
            P("地质公园博物馆", 22.5550, 114.5350),
            P("鹿嘴", 22.5600, 114.5450),
            P("杨梅坑", 22.5480, 114.5300),
        ],
    ),
    dict(
        id="gd-huizhou-lianhuashan",
        name="莲花山",
        province="广东省", city="惠州市", type="山岳",
        difficulty="较易", days="1天", best_season="3-11月", heat=58,
        desc="惠东莲花山，主峰海拔 1336 米，山形如莲瓣。"
             "上半程林道、下半程草坡，山顶视野能看到整个惠东丘陵。",
        waypoints=[
            P("莲花山脚", 23.1200, 115.0300),
            P("半山", 23.1400, 115.0400),
            PEAK("莲花山主峰", 23.1550, 115.0520),
        ],
    ),
    dict(
        id="gd-jiangmen-guifengshan",
        name="圭峰山",
        province="广东省", city="江门市", type="山岳",
        difficulty="入门", days="1天", best_season="全年", heat=66,
        desc="新会圭峰山，玉台寺一带古木成林，山顶可望银洲湖。"
             "路程短、坡度缓，是珠三角周末溜腿的常规选项。",
        waypoints=[
            P("圭峰山门", 22.5450, 113.0150),
            P("玉台寺", 22.5500, 113.0200),
            PEAK("圭峰山主峰", 22.5560, 113.0250, r=0.01),
        ],
    ),
    dict(
        id="gd-chaozhou-fenghuangshan",
        name="凤凰山（潮州）",
        province="广东省", city="潮州市", type="山岳茶园",
        difficulty="中等", days="1天", best_season="3-11月", heat=61,
        desc="潮州凤凰单丛茶的原产地，主峰海拔 1497 米。"
             "穿茶园上山，四五月采茶季最有生活气；山顶常有云，注意保暖。",
        waypoints=[
            P("凤凰镇", 23.7300, 116.6100),
            P("茶园", 23.7400, 116.6200),
            PEAK("凤凰山主峰", 23.7550, 116.6320),
        ],
    ),
    # ============================================================ 江西
    dict(
        id="jx-pingxiang-wugongshan",
        name="武功山·金顶穿越",
        province="江西省", city="萍乡市", type="高山草甸",
        difficulty="难", days="2天", best_season="5-10月", heat=93,
        desc="十万亩高山草甸铺在 1600 米以上，是国内外都少见的景观。"
             "经典走法：沈子村上山，金顶看日出，再沿山脊到发云界。"
             "全程无遮蔽，大风大雨时体感极低，必须带硬壳。",
        waypoints=[
            P("沈子村", 27.4652, 114.1054),
            P("中庵", 27.4600, 114.1580),
            PEAK("金顶", 27.4650, 114.1730),
            P("发云界", 27.4850, 114.2050),
        ],
    ),
    dict(
        id="jx-jiujiang-lushan",
        name="庐山·三叠泉—五老峰",
        province="江西省", city="九江市", type="山岳瀑布",
        difficulty="较难", days="1-2天", best_season="4-11月", heat=88,
        desc="牯岭镇出发，经含鄱口上五老峰，再下到三叠泉看落差 155 米的瀑布。"
             "三叠泉台阶约三千级，下去容易上来难，回程要留足体力。",
        waypoints=[
            P("牯岭镇", 29.5600, 115.9800),
            P("含鄱口", 29.5550, 115.9900),
            PEAK("五老峰", 29.5480, 116.0000),
            P("三叠泉", 29.5300, 115.9880),
        ],
    ),
    dict(
        id="jx-shangrao-sanqingshan",
        name="三清山·南清园—西海岸",
        province="江西省", city="上饶市", type="花岗岩峰林",
        difficulty="中等", days="1-2天", best_season="4-11月", heat=86,
        desc="花岗岩峰林世界自然遗产，巨蟒出山、东方女神是标志景观。"
             "南清园上、西海岸栈道绕行，全程高空栈道多，恐高者慎选。",
        waypoints=[
            P("三清山索道上站", 28.9000, 118.0500),
            P("南清园", 28.9050, 118.0550),
            P("巨蟒出山", 28.9080, 118.0570),
            PEAK("玉京峰", 28.9130, 118.0620),
            P("西海岸", 28.9180, 118.0520),
        ],
    ),
    dict(
        id="jx-jian-jinggangshan",
        name="井冈山·黄洋界",
        province="江西省", city="吉安市", type="红色山林",
        difficulty="较易", days="1天", best_season="4-11月", heat=78,
        desc="茨坪出发上黄洋界，海拔 1343 米，是井冈山五大哨口之一。"
             "沿途竹林与杜鹃混生，云海概率高，路面成熟好走。",
        waypoints=[
            P("茨坪", 26.5700, 114.1200),
            PEAK("黄洋界", 26.5900, 114.1000, r=0.02),
            P("龙潭", 26.5750, 114.1300),
        ],
    ),
    dict(
        id="jx-yichun-mingyueshan",
        name="明月山",
        province="江西省", city="宜春市", type="山岳温泉",
        difficulty="中等", days="1天", best_season="4-11月", heat=76,
        desc="云谷飞瀑一段溪瀑连续，太平山顶海拔 1736 米，"
             "下山后可泡温汤温泉，是江西少见的「爬山＋泡汤」组合。",
        waypoints=[
            P("明月山门", 27.5500, 114.2600),
            P("云谷飞瀑", 27.5650, 114.2700),
            PEAK("太平山顶", 27.5820, 114.2820),
        ],
    ),
    dict(
        id="jx-yingtan-longhushan",
        name="龙虎山",
        province="江西省", city="鹰潭市", type="丹霞道教",
        difficulty="入门", days="1天", best_season="3-11月", heat=74,
        desc="道教正一派祖庭，天师府在上清古镇。泸溪河两岸丹霞崖壁密集，"
             "可坐竹筏也可沿河走，几乎无爬升，适合全家。",
        waypoints=[
            P("上清古镇", 28.0300, 116.9600),
            P("天师府", 28.0350, 116.9650),
            P("仙水岩", 28.0500, 116.9750),
        ],
    ),
    dict(
        id="jx-shangrao-lingshan",
        name="灵山",
        province="江西省", city="上饶市", type="花岗岩",
        difficulty="中等", days="1天", best_season="4-11月", heat=71,
        desc="花岗岩峰林与高山杜鹃，主峰海拔 1496 米。"
             "索道上山后走环线，石人峰一段视野最开阔，人比三清山少很多。",
        waypoints=[
            P("灵山索道下站", 28.4900, 117.8400),
            PEAK("石人峰", 28.5000, 117.8500),
            P("水晶山", 28.5050, 117.8550),
        ],
    ),
    dict(
        id="jx-shangrao-guifeng",
        name="龟峰",
        province="江西省", city="上饶市", type="丹霞",
        difficulty="较易", days="1天", best_season="3-11月", heat=68,
        desc="「江上龟峰天下稀」，丹霞石峰造型密集，清水湖绕山而过。"
             "环线短、爬升小，两三个小时能走完，适合作为婺源的搭配行程。",
        waypoints=[
            P("龟峰景区门", 28.3450, 117.4150),
            PEAK("老人峰", 28.3500, 117.4200, r=0.012),
            P("清水湖", 28.3550, 117.4250),
        ],
    ),
    # ============================================================ 广西桂林
    dict(
        id="gx-guilin-lijiang",
        name="漓江徒步·杨堤—兴坪",
        province="广西壮族自治区", city="桂林市", type="江河田园",
        difficulty="中等", days="1-2天", best_season="3-11月", heat=90,
        desc="漓江最精华的一段，二十元人民币背面取景地就在兴坪。"
             "沿江古道穿村而过，可徒步也可坐竹筏，注意枯水期部分河滩裸露。",
        waypoints=[
            P("杨堤码头", 25.0117, 110.4400),
            P("浪石", 25.0000, 110.4600),
            P("全家洲", 24.9800, 110.4800),
            P("冷水渡", 24.9600, 110.4950),
            P("兴坪古镇", 24.9333, 110.5000),
        ],
    ),
    dict(
        id="gx-guilin-longji",
        name="龙脊梯田·金坑大寨环线",
        province="广西壮族自治区", city="桂林市", type="梯田村寨",
        difficulty="中等", days="1-2天", best_season="4-10月", heat=88,
        desc="金坑红瑶梯田，从大寨上到西山韶乐观景台，落差近八百米。"
             "五月灌水期镜面梯田、九月稻浪各有看头，山上可住吊脚楼。",
        waypoints=[
            P("金坑大寨", 25.7750, 110.1280),
            P("田头寨", 25.7830, 110.1250),
            P("西山韶乐", 25.7900, 110.1230),
            PEAK("金佛顶", 25.7780, 110.1350, r=0.012),
        ],
    ),
    dict(
        id="gx-guilin-maoershan",
        name="猫儿山",
        province="广西壮族自治区", city="桂林市", type="原始森林",
        difficulty="难", days="2天", best_season="5-10月", heat=80,
        desc="华南第一峰，海拔 2142 米，漓江发源地。"
             "老山界一段是红军长征翻越过的山口，山上多雾多雨，需备防水。",
        waypoints=[
            P("桐木坪（山脚）", 25.8692, 110.3706),
            P("老山界", 25.8720, 110.4000),
            PEAK("猫儿山顶", 25.8700, 110.4200),
        ],
    ),
    dict(
        id="gx-yangshuo-yulonghe",
        name="阳朔·遇龙河田园徒步",
        province="广西壮族自治区", city="桂林市", type="田园",
        difficulty="入门", days="1天", best_season="3-11月", heat=85,
        desc="遇龙河两岸是阳朔最安静的田园带，金龙桥到工农桥一路田埂与村道。"
             "骑行为主、徒步也合适，竹筏漂流可以搭配一段。",
        waypoints=[
            P("金龙桥", 24.7900, 110.4000),
            P("旧县", 24.7800, 110.4100),
            P("工农桥", 24.7500, 110.4300),
        ],
    ),
    dict(
        id="gx-guilin-city",
        name="桂林·两江四湖—象鼻山城市徒步",
        province="广西壮族自治区", city="桂林市", type="城市地标",
        difficulty="入门", days="1天", best_season="全年", heat=82,
        desc="桂林市区环水徒步，象鼻山、日月双塔、叠彩山、伏波山串成一线。"
             "全程滨水步道，夜里灯光亮起来更好看，适合半天。",
        waypoints=[
            P("象鼻山", 25.2680, 110.2980),
            P("日月双塔", 25.2780, 110.2960),
            P("叠彩山", 25.2900, 110.3000),
            P("伏波山", 25.2850, 110.3020),
        ],
    ),
    dict(
        id="gx-guilin-zhiyuan-bajiaozhai",
        name="资源·八角寨",
        province="广西壮族自治区", city="桂林市", type="丹霞",
        difficulty="中等", days="1天", best_season="4-11月", heat=70,
        desc="与湖南崀山同属一处丹霞，广西侧从梅溪镇上山。"
             "山顶看「群螺观天」，晨雾时峰丛像浮在云上，日出前上山最值。",
        waypoints=[
            P("梅溪镇", 26.3800, 110.7700),
            PEAK("八角寨顶", 26.4000, 110.7900),
        ],
    ),
]

# ---------------------------------------------------------------- 峰顶海拔
# 公开资料里的主峰海拔，用于校验轨迹是否真的爬到了山顶。
# 轨迹最高点与这里差距过大，说明峰顶坐标或路网有问题，构建时会被判不合格。
PEAK_M = {
    "hn-hengyang-zhurong": 1289,
    "hn-zhangjiajie-jinbianxi": 1080,
    "hn-zhangjiajie-tianmenshan": 1519,
    "hn-shaoyang-langshan": 818,
    "hn-chenzhou-mangshan": 1720,
    "hn-changsha-daweishan": 1607,
    "hn-yueyang-mufushan": 1596,
    "hn-changde-hupingshan": 2099,
    "hn-zhangjiajie-badagongshan": 1890,
    "hn-yongzhou-yangmingshan": 1625,
    "hn-yongzhou-shunhuangshan": 1882,
    "hn-huaihua-xuefengshan": 1934,
    "hn-shaoyang-yunshan": 1372,
    "hn-changsha-yuelushan": 296,
    "hn-changde-taohuayuan": 120,
    "gd-shaoguan-danxiashan": 409,
    "gd-huizhou-luofushan": 1281,
    "gd-shenzhen-wutongshan": 943,
    "gd-shenzhen-qiniangshan": 869,
    "gd-shenzhen-dongxichong": 60,
    "gd-shaoguan-chuanding": 1586,
    "gd-guangzhou-baiyunshan": 382,
    "gd-qingyuan-yingxi": 110,
    "gd-zhaoqing-dinghushan": 1000,
    "gd-foshan-xiaoshan": 344,
    "gd-shaoguan-shikengkong": 1902,
    "gd-huizhou-heipaijiao": 40,
    "gd-shenzhen-dapeng-geopark": 60,
    "gd-huizhou-lianhuashan": 1336,
    "gd-jiangmen-guifengshan": 400,
    "gd-chaozhou-fenghuangshan": 1497,
    "jx-pingxiang-wugongshan": 1918,
    "jx-jiujiang-lushan": 1436,
    "jx-shangrao-sanqingshan": 1819,
    "jx-jian-jinggangshan": 1343,
    "jx-yichun-mingyueshan": 1736,
    "jx-yingtan-longhushan": 130,
    "jx-shangrao-lingshan": 1496,
    "jx-shangrao-guifeng": 300,
    "gx-guilin-lijiang": 400,
    "gx-guilin-longji": 1180,
    "gx-guilin-maoershan": 2142,
    "gx-yangshuo-yulonghe": 200,
    "gx-guilin-city": 220,
    "gx-guilin-zhiyuan-bajiaozhai": 818,
}

for _r in ROUTES:
    _r["peak_m"] = PEAK_M.get(_r["id"])
