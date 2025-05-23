/*
 *   Copyright (c) 2023
 *   Canonical Ltd. (All rights reserved)
 *
 *   This program is free software; you can redistribute it and/or
 *   modify it under the terms of version 2 of the GNU General Public
 *   License published by the Free Software Foundation.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with this program; if not, contact Novell, Inc. or Canonical
 *   Ltd.
 */

#ifndef __AA_COMMON_FLAGS_H
#define __AA_COMMON_FLAGS_H

typedef int optflags_t;

typedef struct optflags {
	optflags_t control;
	optflags_t dump;
	optflags_t warn;
	optflags_t Werror;
} optflags;

extern optflags parseopts;

#endif /* __AA_COMMON_FLAGS_H */
