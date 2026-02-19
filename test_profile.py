#!/usr/bin/env python3
"""
Тестовый скрипт для создания .lprof файла с несколькими функциями
"""

import time
import random
import numpy as np

# Для использования с kernprof -l test_profile.py
# @profile
def slow_function(n=1000000):
    """Медленная функция для профилирования."""
    total = 0
    for i in range(n):
        total += i * i
    return total

# @profile  
def fast_function():
    """Быстрая функция для профилирования."""
    return sum(range(100))

# @profile
def matrix_operations(size=100):
    """Операции с матрицами для профилирования."""
    # Создаем случайные матрицы
    A = np.random.random((size, size))
    B = np.random.random((size, size))
    
    # Умножение матриц
    C = np.dot(A, B)
    
    # Поэлементные операции
    D = A * B
    E = np.sin(A)
    
    return np.sum(C), np.sum(D), np.sum(E)

# @profile
def fibonacci(n):
    """Рекурсивный расчет числа Фибоначчи (неэффективно для больших n)."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def main():
    """Основная функция для демонстрации профилирования."""
    print("Создание тестовых данных профилирования...")
    
    # Запускаем функции для профилирования
    result1 = slow_function(500000)
    print(f"Результат медленной функции: {result1}")
    
    result2 = fast_function()
    print(f"Результат быстрой функции: {result2}")
    
    matrix_result = matrix_operations(50)
    print(f"Результат операций с матрицами: {matrix_result}")
    
    # Число Фибоначчи (только маленькое n для демонстрации)
    fib_result = fibonacci(10)
    print(f"fibonacci(10) = {fib_result}")
    
    print("Тестовые данные профилирования созданы успешно!")

if __name__ == "__main__":
    main()