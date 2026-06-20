// ブログ掲載店舗（推薦結果に一致した場合にリンクを案内するために保持）
const BLOG_SHOPS = {
  '安ざわ家': 'anzawaya-nerima',
  'ラーメン富士丸': 'fujimaru-kamiya',
  '伍福軒': 'gofukuken-ikebukuro',
  'らーめん護什番': 'gojuban-zoshigaya',
  '超ごってり麺 ごっつ': 'gottsu-akihabara',
  'らーめん HAGGY': 'haggy-chofu',
  '銀座はるちゃんラーメン': 'haruchan-ramen-ginza',
  'らぁ麺 はやし田': 'hayashida-ramen-ikebukuro',
  'ひろちゃんラーメン': 'hirochan-ramen-ikebukuro',
  '寿限無': 'jugemu-tantanmen-ueno',
  '開楽本店': 'kailaku-ikebukuro',
  '中華そば 麒麟': 'kirin-ikebukuro',
  'マルQ': 'maruq-nerima',
  'ミゾグチヤ': 'mizoguchiya-higashijujo',
  'なぎちゃんラーメン': 'nagichan-ramen-ekoda',
  'にじゅうぶんのいち': 'nijubun-no-ichi-higashogu',
  'ろく月': 'rokugatu-asakusabashi',
  '新宿シンちゃんラーメン': 'shinchan-shinjuku',
  'RAMEN紫苑': 'shion-takadanobaba',
  'しゅんやっちゃん': 'shunyacchan-takao',
  '豚骨蒼翔': 'sosho-suginami',
  'スタミナラーメン鬼山': 'stamina-oniyama-shibuya',
  'SUPER MEN': 'supermen-iidabashi',
  'すず鬼': 'suzuki-mitaka',
  '麺家たいせい': 'taisei-nakano',
  'たた味': 'tatami-nihonbashi',
  'つじ田': 'tsujita-asa-iidabashi',
};

export const onRequestPost = async (context) => {
  try {
    const body = await context.request.json();
    const userMessage = body.message?.trim();

    if (!userMessage || userMessage.length > 200) {
      return Response.json({ error: 'メッセージが不正です' }, { status: 400 });
    }

    const systemPrompt = `あなたはラーメン専門のAIアシスタントです。
ユーザーの希望（エリア・ジャンル・気分など）をもとに、日本全国のラーメン店を2〜3軒提案してください。

【回答ルール】
- 実在するラーメン店のみ提案する
- 店名・エリア・おすすめポイントをセットで伝える
- フランクで親しみやすい口調で（「〜だよ」「〜かも」「〜がおすすめ！」など）
- 各店舗は短く、でも具体的に説明する
- 日本語で回答する
- 情報が古い場合があるので、訪問前に確認を促す一言を最後に添える`;

    const response = await context.env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userMessage },
      ],
      max_tokens: 700,
    });

    let aiResponse = response.response;

    // ブログ掲載店舗が含まれていればリンクを案内
    const blogMatches = [];
    for (const [name, slug] of Object.entries(BLOG_SHOPS)) {
      if (aiResponse.includes(name)) {
        blogMatches.push(`📖 ${name}はこのブログでも紹介しています → /blog/${slug}`);
      }
    }
    if (blogMatches.length > 0) {
      aiResponse += '\n\n' + blogMatches.join('\n');
    }

    return Response.json({ response: aiResponse });
  } catch (e) {
    console.error(e);
    return Response.json({ error: 'エラーが発生しました。しばらく待ってから試してください。' }, { status: 500 });
  }
};
