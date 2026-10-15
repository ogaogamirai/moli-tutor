# dialogue spine（基本線）— jomon-origin

> 生成: `tutor_cli.py spine`（DAG から機械的下書き）→ **AI 推敲（2026-10-15・型v0.2）**。教材: `G:\マイドライブ\Tools\moli-tutor\materials\jomon-origin\index.html`
> 目的: 短ターンで速く回す会話のレール。**説明1＋山場の問い1**に絞る。

## テンポ規律（v0.2）
- 1ターン = 説明 2〜3文 + **山場の問い1問だけ**（想起の確認はしない）。8割で次へ。
- **予測→答え合わせ**: 「どうなると思う？」を先に。外れても1往復で理解が動く。
- 詰まり=`on_fail`（具体へ浅化）。通過=`on_pass`（次節へ）。
- 指す操作: `act --heading-index N`（beat に埋め込み済み）。
- **先回り**（preempt）: 予測される摩擦は最初の説明で触れる（浅化の往復を消す）。

---

## node idx1 — 序章：日本列島の人類史の「現在地」と独自進化の前提（prerequisite）
- goal: この記事が「一つの歴史的教訓」から始まる意味を掴む＝歴史は“定説”ではなく“証拠”から描き直す、という土台。
- spine:
  - `act` — heading_index 1
  - `ask` — この記事は、何を土台に歴史を組み立てようとしている？（＝“教訓”の中身は？）
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_2
- preempt: —
- shallow_example: 推理小説——犯人は噂では決まらない、証拠で決まる。

## node idx2 — 1. 捏造事件の教訓と、科学が証明する「確かな歴史の始まり」（concept）
- goal: 旧石器捏造事件（2000）を機に、“確かな人類史”は約3万8000年前の現生人類からと確定。“定説”から“証拠”へ歴史の作り方が変わったことを掴む。
- spine:
  - `act` — heading_index 2
  - `ask` — 事件は学界の“痛手”。でもこの記事には“前進”でもある。なぜ？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_3
- preempt: 旧石器（3万8000年前・石器だけ）と縄文（約1万6000年前〜・土器）の時代順を最初に一言。
- shallow_example: 約3万8000年前＝石器だけ（旧石器／岩宿）、約1万6000年前〜＝土器（縄文）。

## node idx3 — 2. 南方海上ルートから到達した「単一祖先集団」（concept）
- goal: “複数移住説”という長年の定説を、核ゲノム解析が覆した。縄文人は“南方ルートの単一集団”だった——“定説が証拠で覆る”2つ目の例を掴む。
- spine:
  - `act` — heading_index 3
  - `ask` — 昔の説は“複数移住”、新しい証拠は“単一系統”。何が決め手で説が変わった？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_4
- preempt: —
- shallow_example: “母系だけの家系図”と“両親からの全体の設計図”。範囲が広がると同じ根と分かる。

## node idx4 — 3. 数万年にわたる深い孤立と「小進化（遺伝的浮動）」（concept）
- goal: では、単一起源であったにもかかわらず、なぜ列島内でDNAの地域差（東西の違いなど）が生まれたのでしょうか。東京大学の研究チームが行ったシミュレーションにより、以下の条件が揃えば、単一の集団でも列島内で大きな遺伝的分化が生じることが実証されま…
- spine:
  - `act` — heading_index 4
  - `ask` — “単一起源”なのに、なぜ列島内でDNAの地域差（東西）が生まれた？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_5
- preempt: —
- shallow_example: 少人数が島に分かれて数万年——偶然で特色が出る（遺伝的浮動）。

## node idx5 — 4. この「前提」が独自性を生んだ根本原因である（prerequisite）
- goal: この「確実な始まり（約3万8000年前）」「単一起源」、そして「数万年にわたる深い孤立」という科学的事実こそが、本レポートの中心的な問いである「なぜ日本列島で独自の適応と進化が起きたのか」を解き明かす最大の鍵となります。
- spine:
  - `act` — heading_index 5
  - `ask` — “確かな始まり・単一起源・深い孤立”——この3つは、なぜ独自進化の鍵になる？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_6
- preempt: —
- shallow_example: 3つの前提が揃うと、外から混ざらず“内で育つ”。

## node idx6 — 第1章：技術の特異性──世界史を覆す早期技術革新（concept）
- goal: 日本列島の人類史は、その幕開けから世界的に極めて特異な技術的到達点を示していました。その特異性を理解するために、まずは縄文時代に先行する「岩宿（いわじゅく）時代」について触れておきましょう。
- spine:
  - `act` — heading_index 6
  - `ask` — 日本列島は“幕開けから”技術的に特異。まず土器の前の、何時代から見る？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_7
- preempt: —
- shallow_example: 縄文の前に岩宿（旧石器）がある。順番で見る。

## node idx7 — 1. 「旧石器時代」の枠に収まらない「岩宿文化」とは（concept）
- goal: 「岩宿時代」とは、一般的に「旧石器時代」と呼ばれる約3万8000年前から約1万6000年前までの日本列島における時代を指します 。1946年、群馬県の岩宿遺跡で石器が発見されたことで、日本にも土器以前の時代が存在したことが初めて証明されまし…
- spine:
  - `act` — heading_index 7
  - `ask` — 1946年の岩宿遺跡の発見は、日本史に何を初めて証明した？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_8
- preempt: —
- shallow_example: 「日本にも石器だけの時代があった」こと。

## node idx8 — 2. 世界最古級の「局部磨製石斧」の衝撃（concept）
- goal: 岩宿文化の始まりを象徴するのが、刃先を丁寧に磨き上げた「局部磨製石斧（きょくぶませいせきふ）」です 。 材料工学としての「研磨」： 打製石器に比べ、刃部を研磨した石斧は木材への食い込みが良く、繊維を断ち切る能力に優れていました。
- spine:
  - `act` — heading_index 8
  - `ask` — 局部磨製石斧の“研磨”は、材料工学として何に効く？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_9
- preempt: —
- shallow_example: 研いだ刃 vs 打ちっぱなし——木への食い込みが違う。

## node idx9 — 3. 「土器革命」──農耕以前の化学プラント（concept）
- goal: 岩宿時代に続く縄文時代の象徴である「土器」もまた、約1万6500年前という世界最古級の年代を誇ります。 文明のパラダイムシフト： 世界史的には「土器は農耕に伴う穀物の保存や煮炊きのために生まれた」と定義されます。
- spine:
  - `act` — heading_index 9
  - `ask` — 世界では“土器は農耕とセット”。日本の土器はどこが例外？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_10
- preempt: 世界の常識「土器＝農耕とセット」を先に置いてから、日本の例外を示す。
- shallow_example: 保存と煮炊きの“化学プラント”を、農耕の前に持った。

## node idx10 — 4. なぜ「日本だけ」早かったのか：孤立環境が生んだ技術圧（concept）
- goal: なぜ、日本列島でこれほど早期に技術革新が起きたのでしょうか。その答えは、序章で確認した「単一起源と深い孤立」にあります 。
- spine:
  - `act` — heading_index 10
  - `ask` — “日本だけ早い”技術革新を可能にした環境条件は何と何？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_11
- preempt: —
- shallow_example: 孤立＝外に頼れない → 自分で作る圧。

## node idx11 — 【事実・仮説・解釈の境界線】（concept）
- goal: 事実（エビデンス）： 日本列島の確実な人類史は現生人類（約3万8000年前）から始まり、原人・旧人の確実な証拠は存在しないこと 。 岩宿文化期の約3万5000年前の地層から局部磨製石斧が出土していること 。
- spine:
  - `act` — heading_index 11
  - `ask` — この記事が毎章「事実・仮説・解釈」を分けるのは、何を守るため？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_12
- preempt: —
- shallow_example: どこまでが“証拠”かを、混ぜないため。

## node idx12 — 第2章：生存戦略──農耕なき高度定住社会の成立（concept）
- goal: 世界史における人類の歩みを振り返ると、「定住」は通常「農耕の開始」とセットで語られます。中東のメソポタミアや中国の長江流域などでは、気候変動による食料不足を乗り越えるために、小麦や稲などの「農耕」を開始し、その農地を管理するために「定住」を…
- spine:
  - `act` — heading_index 12
  - `ask` — 世界の常識は“定住＝農耕”。日本の“農耕なき定住”を支えたのは？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_13
- preempt: 世界の常識「定住＝農耕」を先に置く。日本は“農耕なき定住”。
- shallow_example: 保存と資源管理があれば、農耕がなくても定住できる。

## node idx13 — 1. 土器という「化学プラント」と人口増加の因果関係（concept）
- goal: 縄文人が定住できた最大の理由は、第1章で触れた「土器」を単なる器としてではなく、高度な「化学プラント」として活用したことにあります。
- spine:
  - `act` — heading_index 13
  - `ask` — 土器を“化学プラント”として使うと、なぜ人口増につながる？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_14
- preempt: —
- shallow_example: アク抜き・保存で食料が安定 → 人が増える。

## node idx14 — 2. 「採集」の枠を超える植物管理──アズキとクリの日本独自栽培（concept）
- goal: 縄文人は、森の恵みをただ受動的に「採集」していたわけではありません。近年のゲノム解析や植物考古学により、彼らが植物の遺伝子に介入し、独自の「栽培化」を行っていたことが実証されています。
- spine:
  - `act` — heading_index 14
  - `ask` — “採集”と“栽培”を分ける決め手は、証拠で言うと何？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_15
- preempt: —
- shallow_example: 野生のままか、人が選んで育てたか＝種の変化で分かる。

## node idx15 — 3. 森林資源の高度利用──漆（うるし）と縄（concept）
- goal: 食料だけでなく、生活資材の面でも森林資源を極限まで活用していました。 漆（うるし）技術の確立： 縄文時代前期にはすでに高度な漆工芸技術が存在していました。
- spine:
  - `act` — heading_index 15
  - `ask` — 漆や縄の高度利用は、“定住の深さ”をどう示す？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_16
- preempt: —
- shallow_example: 手間のかかる技術＝そこに長く住んだ証拠。

## node idx16 — 4. 因果関係のまとめ：なぜ「農耕なし」で定住できたのか（concept）
- goal: 世界史の常識と対比すると、その因果関係は明確です。 孤立と多様な自然環境： 外部への移動が制限された島嶼環境に、毒やアクを含むがカロリーの高い森林資源（木の実）と豊富な海洋資源があった。
- spine:
  - `act` — heading_index 16
  - `ask` — “農耕なし”で定住できた因果を、1本の鎖で言うと？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_17
- preempt: —
- shallow_example: 孤立＋多様な自然 → 森林・海の資源 → 保存技術。この鎖。

## node idx17 — 【事実・仮説・解釈の境界線】（concept）
- goal: 事実（エビデンス）： 縄文土器の内部から、魚類や海獣類の脂質（高度不飽和脂肪酸など）が検出されていること。 縄文時代の遺跡から出土するアズキの炭化種子が、時代が下るにつれて大型化し、裂莢性（さやが弾ける性質）を失うという遺伝的変化（栽培化の…
- spine:
  - `act` — heading_index 17
  - `ask` — 第2章で、“事実”はどれで、“解釈”はどの部分？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_18
- preempt: —
- shallow_example: 脂質検出やアズキ大型化＝事実。“だから定住”は解釈。

## node idx18 — 第3章：社会構造──広域ネットワークと福祉社会の成立（concept）
- goal: 日本列島の先住民は、数万年にわたり大陸から遺伝的に孤立した小規模集団でありながら、決して閉鎖的な世界に生きていたわけではありません。最新の科学は、彼らが「石の化学的指名手配（産地特定）」によって裏付けられる長距離交易路を維持し、高度な航海術…
- spine:
  - `act` — heading_index 18
  - `ask` — 孤立した小集団なのに“閉じていない”。何でつながった？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_19
- preempt: “孤立＝閉鎖”と誤解しやすい。交易・航海で開いていたことを先に置く。
- shallow_example: 石の産地をたどると“行き来”が見える。

## node idx19 — 1. 科学が証明する「産地」と「海上ハイウェイ」（concept）
- goal: 黒曜石やヒスイは、産地ごとに固有の化学組成（微量元素の含有量）を持っています。現代の科学者は「蛍光X線分析（XRF）」などの手法を用いて、石器1点ずつの「化学的なカルテ」を作成し、産地を100%に近い精度で特定しています 。
- spine:
  - `act` — heading_index 19
  - `ask` — XRF分析は、石器1点から何を明らかにする？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_20
- preempt: —
- shallow_example: 石の“化学カルテ”で出身地が分かる。

## node idx20 — 2. 日本列島に「航海術」があったとされる科学的根拠（concept）
- goal: なぜ当時の人々に高度な航海術があったと言い切れるのか、そこには地質学と実験考古学による強い裏付けがあります。 地理的・地質学的障壁の突破： 隠岐諸島や神津島は、氷河期の海水準低下時でも、本土との間に深い海峡が残されていました 。
- spine:
  - `act` — heading_index 20
  - `ask` — なぜ“航海術があった”と言い切れる？ 根拠は？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_21
- preempt: —
- shallow_example: 泳げない島に、遠くの石が運ばれている。

## node idx21 — 3. 科学が証明する「福祉社会」の実態（concept）
- goal: 縄文時代の遺跡からは、現代の「福祉」に近い、弱者を慈しむ社会の痕跡が科学的に証明されています。 重傷・障害者の介護痕： 岡山県の津雲貝塚では、サメに襲われ片脚を失ったと思われる人物が、その後もしばらく生存し、丁重に埋葬された形跡が見つかって…
- spine:
  - `act` — heading_index 21
  - `ask` — 縄文に“福祉”があったとする証拠は何？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_22
- preempt: —
- shallow_example: 片脚を失った人の長い生存と、丁重な埋葬。

## node idx22 — 4. 非文字メディアによる情報管理（concept）
- goal: 文字を持たなかったとされる縄文人ですが、彼らは情報の記録と伝達のために高度な「代替メディア」を運用していました。 結縄（けつじょう）と象徴体系： 中国の歴史書『魏志倭人伝』には、日本列島の人々が紐の結び目で記録を行う「結縄」を用いていた記述…
- spine:
  - `act` — heading_index 22
  - `ask` — 文字が無いのに情報管理——その“代替メディア”は？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_23
- preempt: —
- shallow_example: 紐の結び目（結縄）＝文字の代わり。

## node idx23 — 5. 必然としての「社会の高度化」（concept）
- goal: なぜ、彼らはこれほどまでに社会を複雑化させたのでしょうか。それは序章で述べた「孤立」と「小規模性」ゆえの必然でした。
- spine:
  - `act` — heading_index 23
  - `ask` — 社会の高度化は“偶然”か“必然”か。理由は？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_24
- preempt: —
- shallow_example: 小さな集団ほど、結束と役割分担が要る。

## node idx24 — 【事実・仮説・解釈の境界線】（concept）
- goal: 事実（エビデンス）： XRF分析により、岩宿・縄文時代の遺跡から神津島・隠岐・糸魚川など遠方の石材が確実に出土している事実 。 ヒスイ大珠が糸魚川から東日本一帯に流通し、特定の墓に副葬されている分布事実 。
- spine:
  - `act` — heading_index 24
  - `ask` — 第3章で、いちばん強い“移動の証拠”は？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_25
- preempt: —
- shallow_example: 遠くの石材が、ここから出土している。

## node idx25 — 終章：日本列島の独自進化モデル──「農耕なき高度定住社会」の必然性（concept）
- goal: 世界史において、人類が定住し複雑な社会を築くための絶対条件は「農耕（穀物栽培）の開始」であるとされてきました。しかし、日本列島の歴史を最新科学のレンズで覗き込むと、その常識は完全に覆ります。
- spine:
  - `act` — heading_index 25
  - `ask` — “農耕が絶対条件”という世界史の常識を、日本はどう覆す？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_26
- preempt: —
- shallow_example: 条件が違えば、別の道で複雑社会に届く。

## node idx26 — 2. 結論：環境が生んだ“適応の必然”（concept）
- goal: 日本列島の岩宿・縄文文化は、決して世界史の発展段階から「遅れた社会」ではありません。 四方を海に囲まれた島嶼という特殊な環境圧に対し、人類がその初期ポテンシャル（航海術・広域移動）を、身体的適応、材料工学、そして高度な社会契約へと全方位に最…
- spine:
  - `act` — heading_index 26
  - `ask` — 日本は“遅れた社会”か？ 記事の結論を一言で。
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_27
- preempt: —
- shallow_example: 遅れではなく、“別ルートの到達点”。

## node idx27 — 【事実・仮説・解釈の境界線】（concept）
- goal: 事実（エビデンス）： 約2万6000年前の北海道に、シベリアや大陸と共通点を持つ細石刃技術が出現している事実 。 LGM（最終氷期最盛期）にロシア・トランスバイカル地方が人類の無居住地（無人の地）となっていた事実 。
- spine:
  - `act` — heading_index 27
  - `ask` — 終章の結論を支える“事実”は何？
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_28
- preempt: —
- shallow_example: 細石刃技術・無居住地——証拠が結論を支える。

## node idx28 — 参考文献（学術論文・資料）（concept）
- goal: **【遺伝学・ゲノム解析】 Kim et al.(2024:) : "Genetic Analysis of a Yayoi Individual from the Doigahama Site Provides Insights into…
- spine:
  - `act` — heading_index 28
  - `ask` — （参考文献。学びの対象外ならスキップ可）
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: KC_jomon-origin_29
- preempt: —
- shallow_example: 論文・分析手法の一覧＝主張の土台。

## node idx29 — あなたへのおすすめ（concept）
- goal: 出典: https://note.com/sousinsha_2025/n/nfa9dec5513e4
- spine:
  - `act` — heading_index 29
  - `ask` — （note の関連記事。学びの対象外／スキップ可）
  - `on_fail` — 浅化: 具体例・身近な例に1段下げる（shallow_example 参照）
  - `on_pass` — 次へ: END
- preempt: —
- shallow_example: 外部リンク。
