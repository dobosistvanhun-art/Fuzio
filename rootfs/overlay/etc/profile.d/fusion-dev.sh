# FusionOS — fejlesztői eszközök (fusion-dev): Node.js a DATA-n, az npm globális csomagjai a saját mappában
case ":$PATH:" in *:/data/dev/node/bin:*) ;; *) PATH="/data/dev/node/bin:$HOME/.local/bin:$PATH" ;; esac
export PATH NPM_CONFIG_PREFIX="$HOME/.local"
