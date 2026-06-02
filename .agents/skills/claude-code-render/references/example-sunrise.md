# Example I. sunrise()

A function whose body is also a landscape. Comments are clouds, identifiers form mountains, regex content is the sun, string returns are layered water. The function "returns the sunrise" three times because oceans have depth.

Technique: four-color composition in one fence. The semantic names (`halo`, `core`, `horizon`) double as labels for parts of the picture.

````
```javascript
function sunrise() {
  // ⢀⣠⣤⣄⡀                            ⢀⣠⣤⣄⡀
  // ⠘⠿⠿⠟⠁                            ⠈⠻⠿⠟⠁
  //
  //                  ⢀⣀⣤⣤⣄⡀
  //               ⢀⣴⣾⣿⣿⣿⣿⣷⡆
  const halo = /⢠⣾⣿⣿⣿⣿⣿⣿⣿⣷/g;
  const core = /⠈⠻⠿⣿⣿⣿⣿⠿⠟⠁/g;
  //
  let horizon = ⣀⣀⣀⣠⣤⣴⣶⣾⣿⣿⣷⣶⣶⣶⣦⣤⣄⣀⣀⣀;
  //
  return "⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶";
  return "⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶";
  return "⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿";
}
```
````

Expected rendering:

- Gray clouds (comment lines).
- Orange-yellow sun (regex contents inside `/.../g`).
- White mountain silhouette (identifier characters after `let horizon =`).
- Green water bands (three string returns).
- Orange keywords (`function`, `const`, `let`, `return`) and the `=`, `(`, `)`, `{`, `}`, `;` punctuation form structural scaffolding.

Repro notes:

- Language tag must be `javascript`. `js` may or may not work depending on highlighter aliases.
- The braille identifier after `let horizon =` is non-standard JS. The highlighter accepts it as identifier-class anyway because it tokenizes by character class, not strict JS lexer rules.
- Multiple `return` statements are unreachable but parse. They are required to get three lines of green water.
