import resolve from 'rollup-plugin-node-resolve';
import typescript from 'rollup-plugin-typescript2';
import babel from 'rollup-plugin-babel';
import { terser } from "rollup-plugin-terser";
import gzipPlugin from 'rollup-plugin-gzip'

export default {
    input: ['src/main.ts'],
    output: {
        dir: './custom_components/hacs/frontend/experimental',
        format: 'es',
    },
    plugins: [
        gzipPlugin(),
        resolve(),
        typescript(),
        babel({
            exclude: 'node_modules/**'
        }),
        terser()]
};