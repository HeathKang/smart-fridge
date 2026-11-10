import icon0 from '@twemoji/svg/1f95a.svg';
import icon1 from '@twemoji/svg/1f95b.svg';
import icon2 from '@twemoji/svg/1f345.svg';
import icon3 from '@twemoji/svg/1f954.svg';
import icon4 from '@twemoji/svg/1f360.svg';
import icon5 from '@twemoji/svg/1f955.svg';
import icon6 from '@twemoji/svg/1f33d.svg';
import icon7 from '@twemoji/svg/1f952.svg';
import icon8 from '@twemoji/svg/1f346.svg';
import icon9 from '@twemoji/svg/1f966.svg';
import icon10 from '@twemoji/svg/1f9c5.svg';
import icon11 from '@twemoji/svg/1f9c4.svg';
import icon12 from '@twemoji/svg/1fad1.svg';
import icon13 from '@twemoji/svg/1f344.svg';
import icon14 from '@twemoji/svg/1f96c.svg';
import icon15 from '@twemoji/svg/1f34e.svg';
import icon16 from '@twemoji/svg/1f34c.svg';
import icon17 from '@twemoji/svg/1f34a.svg';
import icon18 from '@twemoji/svg/1f34b.svg';
import icon19 from '@twemoji/svg/1f353.svg';
import icon20 from '@twemoji/svg/1f347.svg';
import icon21 from '@twemoji/svg/1f349.svg';
import icon22 from '@twemoji/svg/1f351.svg';
import icon23 from '@twemoji/svg/1f350.svg';
import icon24 from '@twemoji/svg/1f96d.svg';
import icon25 from '@twemoji/svg/1f34d.svg';
import icon26 from '@twemoji/svg/1f95d.svg';
import icon27 from '@twemoji/svg/1f951.svg';
import icon28 from '@twemoji/svg/1f990.svg';
import icon29 from '@twemoji/svg/1f980.svg';
import icon30 from '@twemoji/svg/1f41f.svg';
import icon31 from '@twemoji/svg/1f9aa.svg';
import icon32 from '@twemoji/svg/1f357.svg';
import icon33 from '@twemoji/svg/1f969.svg';
import icon34 from '@twemoji/svg/1f35e.svg';
import icon35 from '@twemoji/svg/1f35a.svg';
import icon36 from '@twemoji/svg/1f35c.svg';
import icon37 from '@twemoji/svg/1fad8.svg';
import icon38 from '@twemoji/svg/1f95f.svg';
import icon39 from '@twemoji/svg/1f36f.svg';
import icon40 from '@twemoji/svg/1f957.svg';

// Twemoji SVG assets are bundled locally; matching does not use a model.
const foodIcons: Array<[RegExp, string]> = [
  [/鸡蛋|鸭蛋|鹌鹑蛋|鹅蛋/, icon0], [/牛奶|酸奶|奶酪|芝士/, icon1],
  [/番茄|西红柿/, icon2], [/土豆|马铃薯/, icon3], [/红薯|地瓜|番薯/, icon4],
  [/胡萝卜|红萝卜/, icon5], [/玉米/, icon6], [/黄瓜/, icon7], [/茄子/, icon8],
  [/西兰花|花椰菜/, icon9], [/洋葱/, icon10], [/大蒜|蒜头/, icon11], [/辣椒|青椒|甜椒/, icon12],
  [/蘑菇|香菇|金针菇|菌菇/, icon13], [/白菜|生菜|菠菜|青菜|油菜|芹菜|韭菜|莴苣|叶菜|卷心菜/, icon14],
  [/苹果/, icon15], [/香蕉/, icon16], [/橙|橘|柑|桔/, icon17], [/柠檬/, icon18],
  [/草莓/, icon19], [/葡萄/, icon20], [/西瓜/, icon21], [/桃子|水蜜桃/, icon22], [/梨/, icon23],
  [/芒果/, icon24], [/菠萝|凤梨/, icon25], [/猕猴桃|奇异果/, icon26], [/牛油果/, icon27],
  [/虾/, icon28], [/螃蟹|蟹肉/, icon29], [/鱼|三文鱼/, icon30], [/贝|扇贝/, icon31],
  [/鸡肉|鸡翅|鸡腿|鸡胸|整鸡/, icon32], [/牛肉|牛排|猪肉|排骨|羊肉|肉片|肉馅/, icon33],
  [/面包|吐司/, icon34], [/米饭|大米/, icon35], [/面条|面粉|意面/, icon36], [/豆腐|豆干/, icon37],
  [/水饺|饺子/, icon38], [/蜂蜜/, icon39],
];

export function foodIcon(name: string): string {
  return foodIcons.find(([pattern]) => pattern.test(name))?.[1] ?? icon40;
}
