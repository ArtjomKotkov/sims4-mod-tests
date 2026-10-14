// Собирает dist/EasyCheats.package: тюнинг пункта «Easy Cheats» в меню сима + строки (STBL) на всех языках.
// Запуск: cd tools/package && npm install && node build-package.js
const fs = require('fs');
const path = require('path');
const { Package, XmlResource, StringTableResource } = require('@s4tk/models');
const { TuningResourceType, BinaryResourceType, StringTableLocale } = require('@s4tk/models/enums');
const { fnv32, fnv64 } = require('@s4tk/hashing');

const ROOT = path.resolve(__dirname, '..', '..');
const INTERACTION_NAME = 'EasyCheats:Interaction_OpenMenu';
const INTERACTION_ID = fnv64(INTERACTION_NAME, true);
const DISPLAY_NAME_KEY = fnv32('EasyCheats:OpenMenu_DisplayName');
const DISPLAY_NAME = 'Easy Cheats';

const LOCALES = [
  'English', 'ChineseSimplified', 'ChineseTraditional', 'Czech', 'Danish', 'Dutch', 'Finnish', 'French',
  'German', 'Italian', 'Japanese', 'Korean', 'Norwegian', 'Polish', 'Portuguese', 'Russian', 'Spanish', 'Swedish',
];

const xml = fs.readFileSync(path.join(ROOT, 'src', 'tuning', 'open_menu_interaction.xml'), 'utf8')
  .replace('{{NAME}}', INTERACTION_NAME)
  .replace('{{ID}}', INTERACTION_ID.toString())
  .replace('{{DISPLAY_NAME_KEY}}', '0x' + DISPLAY_NAME_KEY.toString(16).toUpperCase().padStart(8, '0'));

const pkg = new Package();
pkg.add({ type: TuningResourceType.Interaction, group: 0, instance: INTERACTION_ID }, new XmlResource(xml));

// Отдельная таблица строк для каждого языка игры, иначе в не-английской игре пункт будет без названия.
const stblBase = fnv64('EasyCheats:Strings') & 0x00FFFFFFFFFFFFFFn;
for (const locale of LOCALES) {
  const stbl = new StringTableResource([{ key: DISPLAY_NAME_KEY, value: DISPLAY_NAME }]);
  const instance = StringTableLocale.setHighByte(StringTableLocale[locale], stblBase);
  pkg.add({ type: BinaryResourceType.StringTable, group: 0x80000000, instance }, stbl);
}

const out = path.join(ROOT, 'dist', 'EasyCheats.package');
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, pkg.getBuffer());
console.log('Готово:', out);
console.log('INTERACTION_ID =', INTERACTION_ID.toString());
