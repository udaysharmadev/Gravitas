// GRAVITAS Calculator Tests — Pillar 5: Evidence Before Claims
// Run: node test.js

(function() {
    'use strict';

    var passed = 0;
    var failed = 0;

    function assert(condition, name) {
        if (condition) {
            passed++;
            console.log('  ✓ ' + name);
        } else {
            failed++;
            console.log('  ✗ ' + name);
        }
    }

    function formatNumber(num) {
        if (num === 'Error') return 'Error';
        var n = parseFloat(num);
        if (isNaN(n)) return 'Error';
        if (!isFinite(n)) return 'Error';
        return String(Math.round(n * 1e12) / 1e12);
    }

    function calculate(a, op, b) {
        var x = parseFloat(a);
        var y = parseFloat(b);
        if (isNaN(x) || isNaN(y)) return 'Error';
        switch (op) {
            case '+': return x + y;
            case '-': return x - y;
            case '×': return x * y;
            case '÷': return y === 0 ? 'Error' : x / y;
            case '%': return y === 0 ? 'Error' : x % y;
            default: return y;
        }
    }

    console.log('\nGRAVITAS Calculator — Test Suite\n');

    // Basic operations
    console.log('Basic operations:');
    assert(calculate('5', '+', '3') === 8, '5 + 3 = 8');
    assert(calculate('10', '-', '4') === 6, '10 - 4 = 6');
    assert(calculate('6', '×', '7') === 42, '6 × 7 = 42');
    assert(calculate('20', '÷', '4') === 5, '20 ÷ 4 = 5');

    // Edge cases
    console.log('\nEdge cases:');
    assert(calculate('10', '÷', '0') === 'Error', 'Division by zero → Error');
    assert(calculate('0', '+', '0') === 0, '0 + 0 = 0');
    assert(calculate('0', '×', '999') === 0, '0 × 999 = 0');
    assert(calculate('100', '%', '3') === 1, '100 % 3 = 1');

    // Floating point precision
    console.log('\nFloating point precision:');
    assert(formatNumber(0.1 + 0.2) === '0.3', '0.1 + 0.2 = 0.3 (not 0.30000000000000004)');
    assert(formatNumber(0.3 - 0.1) === '0.2', '0.3 - 0.1 = 0.2');
    assert(formatNumber(0.1 * 3) === '0.3', '0.1 × 3 = 0.3');

    // Negative numbers
    console.log('\nNegative numbers:');
    assert(calculate('-5', '+', '3') === -2, '-5 + 3 = -2');
    assert(calculate('5', '-', '8') === -3, '5 - 8 = -3');
    assert(calculate('-3', '×', '4') === -12, '-3 × 4 = -12');

    // Large numbers
    console.log('\nLarge numbers:');
    assert(calculate('999999', '+', '1') === 1000000, '999999 + 1 = 1000000');
    assert(formatNumber(1e15 + 1) === '1000000000000001', 'Large number precision');

    // Summary
    console.log('\n' + '─'.repeat(40));
    console.log('Results: ' + passed + ' passed, ' + failed + ' failed');
    console.log(failed === 0 ? '✓ All tests pass' : '✗ Some tests failed');
    process.exit(failed === 0 ? 0 : 1);
})();
