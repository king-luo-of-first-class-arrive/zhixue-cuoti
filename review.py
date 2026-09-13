"""SM-2 间隔重复算法（遗忘曲线）。纯函数，无依赖。"""


def sm2(quality, repetition, interval, ease):
    """按本次回忆质量(0-5)返回更新后的 (repetition, interval, ease)。

    quality >= 3 算记住，间隔按 ease 递增；否则重置。interval 单位为天。
    """
    if quality < 3:
        return 0, 1, ease
    ease = max(1.3, ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if repetition == 0:
        return 1, 1, ease
    if repetition == 1:
        return 2, 6, ease
    return repetition + 1, round(interval * ease), ease


if __name__ == "__main__":
    r, i, e = sm2(5, 0, 0, 2.5)
    assert (r, i) == (1, 1), (r, i)
    r, i, e = sm2(5, 1, 1, e)
    assert (r, i) == (2, 6), (r, i)
    r, i, e = sm2(2, 2, 6, e)
    assert (r, i) == (0, 1), (r, i)
    _, _, e = sm2(0, 0, 0, 1.3)
    assert e == 1.3, e
    print("SM-2 自检通过 OK")
