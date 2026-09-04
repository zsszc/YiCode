from fastapi import HTTPException, status


class YiCodeException(HTTPException):
    """YiCode 业务异常基类。"""
    pass


class ProblemNotFound(YiCodeException):
    def __init__(self, problem_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"题目 #{problem_id} 不存在",
        )


class ProgressNotFound(YiCodeException):
    def __init__(self, problem_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"题目 #{problem_id} 的进度记录不存在",
        )


class InvalidReviewScore(YiCodeException):
    def __init__(self, score: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的复习打分: {score}，必须是 easy/ok/hard 之一",
        )


class InvalidFirstSolveStatus(YiCodeException):
    def __init__(self, status: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的首次刷完状态: {status}，必须是 forgot/shaky/solid 之一",
        )
