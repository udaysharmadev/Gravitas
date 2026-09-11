// GRAVITAS Calculator — no eval(), state machine parser
// Built by Antigravity following the GRAVITAS protocol

(function() {
    'use strict';

    const display = document.getElementById('display');
    const buttons = document.querySelectorAll('.btn');

    let current = '0';
    let previous = '';
    let operator = null;
    let shouldResetDisplay = false;

    function updateDisplay() {
        display.textContent = current;
    }

    function formatNumber(num) {
        if (num === 'Error') return 'Error';
        const n = parseFloat(num);
        if (isNaN(n)) return 'Error';
        if (!isFinite(n)) return 'Error';
        // Handle floating point precision (0.1 + 0.2 = 0.3, not 0.30000000000000004)
        return String(Math.round(n * 1e12) / 1e12);
    }

    function calculate(a, op, b) {
        const x = parseFloat(a);
        const y = parseFloat(b);
        if (isNaN(x) || isNaN(y)) return 'Error';

        switch (op) {
            case '+': return x + y;
            case '-': case '−': return x - y;
            case '×': return x * y;
            case '÷':
                if (y === 0) return 'Error';
                return x / y;
            case '%':
                if (y === 0) return 'Error';
                return x % y;
            default: return y;
        }
    }

    function handleNumber(value) {
        if (shouldResetDisplay) {
            current = value;
            shouldResetDisplay = false;
        } else {
            current = current === '0' ? value : current + value;
        }
        updateDisplay();
    }

    function handleDecimal() {
        if (shouldResetDisplay) {
            current = '0.';
            shouldResetDisplay = false;
            updateDisplay();
            return;
        }
        if (!current.includes('.')) {
            current += '.';
            updateDisplay();
        }
    }

    function handleOperator(value) {
        if (operator && !shouldResetDisplay) {
            const result = calculate(previous, operator, current);
            current = formatNumber(result);
            updateDisplay();
            previous = current;
        } else {
            previous = current;
        }
        operator = value;
        shouldResetDisplay = true;
    }

    function handleEquals() {
        if (!operator || shouldResetDisplay) return;
        const result = calculate(previous, operator, current);
        current = formatNumber(result);
        previous = '';
        operator = null;
        shouldResetDisplay = true;
        updateDisplay();
    }

    function handleClear() {
        current = '0';
        previous = '';
        operator = null;
        shouldResetDisplay = false;
        updateDisplay();
    }

    function handleDelete() {
        if (current.length === 1 || current === 'Error') {
            current = '0';
        } else {
            current = current.slice(0, -1);
        }
        updateDisplay();
    }

    // Event listeners
    buttons.forEach(function(btn) {
        btn.addEventListener('click', function() {
            var action = this.dataset.action;
            var value = this.dataset.value;

            switch (action) {
                case 'number': handleNumber(value); break;
                case 'decimal': handleDecimal(); break;
                case 'operator': handleOperator(value); break;
                case 'equals': handleEquals(); break;
                case 'clear': handleClear(); break;
                case 'delete': handleDelete(); break;
            }
        });
    });

    // Keyboard support
    document.addEventListener('keydown', function(e) {
        if (e.key >= '0' && e.key <= '9') handleNumber(e.key);
        else if (e.key === '.') handleDecimal();
        else if (e.key === '+' || e.key === '-' || e.key === '*' || e.key === '/') {
            var opMap = { '+': '+', '-': '-', '*': '×', '/': '÷' };
            handleOperator(opMap[e.key]);
        }
        else if (e.key === 'Enter' || e.key === '=') handleEquals();
        else if (e.key === 'Escape' || e.key === 'c' || e.key === 'C') handleClear();
        else if (e.key === 'Backspace') handleDelete();
        else if (e.key === '%') handleOperator('%');
    });

})();
