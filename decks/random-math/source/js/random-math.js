function substitute(text, variables, tex) {
  let subs = text.match(/\$[a-zA-Z][a-zA-Z0-9]*/g);
  if (subs) {
    for (let j = 0; j < subs.length; j++) {
      if (["$if", "$else", "$endif", "$graph", "$decimal"].includes(subs[j])) {
        continue;
      }
      let obj = variables[subs[j]]
      let val;
      if (tex) {
        val = obj.toTeX();
      } else {
        val = "(" + obj.text() + ")";
      }
      text = text.replace(subs[j], val);
    }
  }
  return text;
}

function substituteEvals(text, variables) {
  let evals = text.match(/\$\{(.+?)\}/g);
  if (evals) {
    for (let j = 0; j < evals.length; j++) {
      let expr = evals[j].substring(2, evals[j].length - 1);
      let obj = nerdamer(substitute(expr, variables, false));
      text = text.replace(evals[j], obj.toTeX());
    }
  }
  return text;
}

// Evaluate a condition
function evalCond(cond, variables) {

  cond = cond.replace(/(^ *| *$)/g, "");
  while (cond[0] === "(" && cond[cond.length - 1] === ")") {
    let remove = true;
    let nest = 1;
    for (let i = 1; i < cond.length - 1; i++) {
      if (cond[i] === "(") {
        nest++;
      } else if (cond[i] === ")") {
        nest--;
      }
      if (!nest) {
        remove = false;
        break;
      }
    }
    if (remove) {
      cond = cond.substring(1, cond.length - 1);
    } else {
      break;
    }
  }

  let nest = 0;
  for (let i = 0; i < cond.length; i++) {
    if (cond[i] === "(") {
      nest++;
    } else if (cond[i] === ")") {
      nest--;
    } else if (!nest) {
      let comp = cond.substring(i).match(/^ (eq|lt|gt|lte|gte) /);
      let compbool = cond.substring(i).match(/^( (and|or)|not) /);
      if (comp) {
        let a = evalCond(cond.substring(0, i), variables);
        let b = evalCond(cond.substring(i + comp[0].length), variables);
        switch (comp[1]) {
          case "eq":
            return a.eq(b);
          case "lt":
            return a.lt(b);
          case "gt":
            return a.gt(b);
          case "lte":
            return a.lte(b);
          case "gte":
            return a.gte(b);
        }
      } else if (compbool) {
        let b = evalCond(cond.substring(i + compbool[0].length), variables);
        if (compbool[0] === "not ") {
          return !b;
        }
        let a = evalCond(cond.substring(0, i), variables);
        if (compbool[0] === " and ") {
          return a && b;
        }
        return a || b;
      }
    }
  }

  cond = substitute(cond, variables, false);
  return nerdamer(cond);
}

function generateRandoms() {
  let calc = document.getElementById("calc")
                 .textContent
                 .replace(/\/\*.*?\*\//g, "")
                 .replace(/\r?\n|\r|\t| /g, "");

  // Generate random numbers
  let rands = calc.match(/r\(-?[0-9]+,-?[0-9]+\)/g);
  if (rands) {
    for (let i = 0; i < rands.length; i++) {
      let ms = rands[i].match(/-?[0-9]+/g);
      let min = parseInt(ms[0]);
      let max = parseInt(ms[1]);
      let rand;
      if (!Persistence.isAvailable()) {
        let today = new Date();
        let seed = "" + today.getFullYear() + today.getMonth() + today.getDate() + i;
        Math.seedrandom(seed);
      }
      rand = Math.floor(Math.random()*(max - min + 1) + min);
      calc = calc.replace(rands[i], rand);
    }
  }
  document.getElementById("calc").textContent = calc;
}

// Calculate
function calculate() {

  let vars = {};

  let calc = document.getElementById("calc").textContent;

  // Evaluate variables
  calc = calc.split(";");
  for (let i = 0; i < calc.length; i++) {
    if (calc[i]) {
      let varnameMatch = calc[i].match(/^\s*([a-zA-Z][a-zA-Z0-9]*)\s*=/);
      if (varnameMatch) {
        let varname = varnameMatch[1];
        let expr = calc[i].substring(varnameMatch[0].length).replace(/^\s*=\s*/, "");
        expr = substitute(expr, vars, false);
        vars["$" + varname] = nerdamer(expr);
      }
    }
  }

  // Conditional elements
  let sub = document.getElementById("sub");
  let oldText = sub.innerHTML;
  let newText = "";
  let append = true;
  let nest = 0;
  for (let j = 0; j < oldText.length; j++) {
    let ifm = oldText.substring(j).match(/^\$if /);
    let elsem = oldText.substring(j).match(/^\$else:/);
    let endif = oldText.substring(j).match(/^\$endif/);
    if (ifm) {
      if (append) {
        j += 4;
        let cond = oldText.substring(j).match(/.+?(?=:)/);
        if (!evalCond(cond[0], vars)) {
          append = false;
        }
        j += cond[0].length;
      } else {
        nest++;
      }
    } else if (elsem) {
      if (append) {
        append = false;
      } else if (!nest) {
        append = true;
      }
      j += 5;
    } else if (endif) {
      if (!append) {
        if (!nest) {
          append = true;
        } else {
          nest--;
        }
      }
      j += 5;
    } else if (append) {
      newText += oldText[j];
    }
  }
  sub.innerHTML = newText;

  // Set graph divs
  let graphsFns = [];
  let graphs = sub.innerHTML.match(/\$graph\{.+?\}/g);
  if (graphs) {
    for (let j = 0; j < graphs.length; j++) {
      sub.innerHTML = sub.innerHTML.replace(graphs[j], "<div id=\"graph" + j + "\"></div>");
      let fnsText = substitute(graphs[j].substring(7, graphs[j].length - 1), vars, false).split(";");
      let fns = [];
      for (let fnText of fnsText) {
        fns.push({ fn: fnText });
      }
      graphsFns.push(fns);
    }
  }

  // Evaluate ${}
  let evals = sub.innerHTML.match(/\$\{.+?\}/g);
  if (evals) {
    for (let j = 0; j < evals.length; j++) {
      let evaled = nerdamer(substitute(evals[j].substring(2, evals[j].length - 1), vars, false)).toTeX();
      sub.innerHTML = sub.innerHTML.replace(evals[j], evaled);
    }
  }

  // Evaluate $decimal{}
  let decimals = sub.innerHTML.match(/\$decimal\{.+?\}/g);
  if (decimals) {
    for (let j = 0; j < decimals.length; j++) {
      let evaled = nerdamer(substitute(decimals[j].substring(9, decimals[j].length - 1), vars, false)).text("decimals");
      sub.innerHTML = sub.innerHTML.replace(decimals[j], evaled);
    }
  }

  // Substitute varialbes
  sub.innerHTML = substitute(sub.innerHTML, vars, true);

  // Draw graphs;
  for (let j = 0; j < graphsFns.length; j++) {
    console.log(graphsFns[j]);
    functionPlot({
      target: "#graph" + j,
      grid: true,
      data: graphsFns[j]
    });
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { evalCond, generateRandoms, calculate };
}
