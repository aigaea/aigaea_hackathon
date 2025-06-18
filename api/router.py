#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from api.ai import router as ai_router
from api.emotion import router as emotion_router

# v1 = APIRouter()
router = APIRouter(prefix="/api")

router.include_router(ai_router, prefix="/ai", tags=["AI"])
router.include_router(emotion_router, prefix="/emotion", tags=["Emotion"])
