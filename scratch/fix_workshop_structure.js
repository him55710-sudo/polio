const fs = require('fs');
const path = 'c:\\Users\\임현수\\Downloads\\polio for real\\polio for real\\frontend\\src\\pages\\Workshop.tsx';
const content = fs.readFileSync(path, 'utf8').split('\n');

// Deleting ranges (1-indexed in my thought, 0-indexed in array)
// Range 1: 2062 to 2124 (indices 2061 to 2123)
// Range 2: 2243 to 2292 (indices 2242 to 2291)

const newContent = [
  ...content.slice(0, 2061),
  ...content.slice(2124, 2242),
  ...content.slice(2292)
];

fs.writeFileSync(path, newContent.join('\n'), 'utf8');
console.log('Fixed Workshop.tsx structural corruption.');
