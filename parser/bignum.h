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
 *   along with this program; if not, contact Canonical Ltd.
 */

#ifndef __AA_BIGNUM_H
#define __AA_BIGNUM_H

#include <iostream>
#include <vector>
#include <sstream>
#include <algorithm>
#include <string>

class bignum
{
public:
	std::vector<uint8_t> data;
	uint8_t base;
	bool negative = false;
	bignum () : base(0) {}

	bignum (unsigned long val) {
		if (val == 0)
			data.push_back(val);
		else {
			while(val > 0) {
				data.push_back(val % 10);
				val /= 10;
			}
		}
		base = 10;
	}

	bignum (const char *val) {
		while (*val) {
			data.push_back(*val - 48);
			val++;
		}
		std::reverse(data.begin(), data.end());
		base = 10;
	}

	bignum (const uint8_t val[16]) {
		size_t i;
		bool flag = true;
		for (i = 0; i < 16; i++) {
			if (flag && (val[i] & 0xF0) >> 4 != 0)
				flag = false;
			if (!flag)
				data.push_back((val[i] & 0xF0) >> 4);
			if (flag && (val[i] & 0x0F) != 0)
				flag = false;
			if (!flag)
				data.push_back(val[i] & 0x0F);
		}
		std::reverse(data.begin(), data.end());
		base = 16;
	}

	bignum operator+(const bignum &brhs) const {
		bignum b1 = this->size() < brhs.size() ? *this : brhs;
		bignum b2 = this->size() < brhs.size() ? brhs : *this;
		bignum result;
		result.base = this->base;
		uint8_t carryover = 0;
		uint8_t sum;
		size_t i;
		for (i = 0; i < b1.size(); i++) {
			sum = b1[i] + b2[i] + carryover;
			if (sum > base - 1)
				carryover = 1;
			else
				carryover = 0;
			result.data.push_back(sum % base);
		}
		for (; i < b2.size(); i++) {
			sum = b2[i] + carryover;
			if (sum > base - 1)
				carryover = 1;
			else
				carryover = 0;
			result.data.push_back(sum % base);
		}
		if (carryover != 0)
			result.data.push_back(carryover);
		return result;
	}

	bignum operator-(const bignum &brhs) const {
		bignum b1 = this->size() < brhs.size() ? *this : brhs;
		bignum b2 = this->size() < brhs.size() ? brhs : *this;
		bignum result;
		result.negative = *this < brhs;
		result.base = this->base;
		int8_t borrow = 0;
		int8_t sub;
		size_t i;
		for (i = 0; i < b1.size(); i++) {
			sub = b2[i] - b1[i] - borrow;
			if (sub < 0) {
				sub += base;
				borrow = 1;
			} else
				borrow = 0;
			result.data.push_back(sub);
		}
		for (; i < b2.size(); i++) {
			sub = b2[i] - borrow;
			if (sub < 0) {
				sub += base;
				borrow = 1;
			} else
				borrow = 0;
			result.data.push_back(sub);
		}
		if (borrow) {
			int8_t tmp = result.data[result.size() - 1] -= base;
			tmp *= -1;
			result.data[result.size() - 1] = tmp;
		}
		while (result.size() > 1 && result.data[result.size() - 1] == 0)
			result.data.pop_back();

		return result;
	}
	bool operator>=(const bignum &rhs) const {
		return cmp_bignum(this->data, rhs.data) >= 0;
	}
	bool operator<=(const bignum &rhs) const {
		return cmp_bignum(this->data, rhs.data) <= 0;
	}
	bool operator>(const bignum &rhs) const {
		return cmp_bignum(this->data, rhs.data) > 0;
	}
	bool operator<(const bignum &rhs) const {
		return cmp_bignum(this->data, rhs.data) < 0;
	}
	int operator[](int index) const {
		return this->data[index];
	}
	friend std::ostream &operator<<(std::ostream &os, bignum &bn);
	size_t size() const {
		return data.size();
	}

	/*
	  returns:
	  - 0, if the lhs and rhs are equal;
	  - a negative value if lhs is less than rhs;
	  - a positive value if lhs is greater than rhs.
	*/
	int cmp_bignum(std::vector<uint8_t> lhs, std::vector<uint8_t> rhs) const
	{
		if (lhs.size() > rhs.size())
			return 1;
		else if (lhs.size() < rhs.size())
			return -1;
		else {
			/* assumes the digits are stored in reverse order */
			std::reverse(lhs.begin(), lhs.end());
			std::reverse(rhs.begin(), rhs.end());
			for (size_t i = 0; i < lhs.size(); i++) {
				if (lhs[i] > rhs[i])
					return 1;
				if (lhs[i] < rhs[i])
					return -1;
			}
		}
		return 0;
	}

	static bignum lower_bound_regex(bignum val)
	{
		/* single digit numbers reduce to 0 */
		if (val.size() == 1) {
			val.data[0] = 0;
			return val;
		}

		for (auto& j : val.data) {
			uint8_t tmp = j;
			j = 0;
			if (tmp != val.base - 1) {
				break;
			}
			if (&j == &val.data[val.size()-2]) {
				val.data[val.size()-1] = 1;
				break;
			}
		}
		return val;

	}

	static bignum upper_bound_regex(bignum val)
	{
		for (auto& j : val.data) {
			uint8_t tmp = j;
			j = val.base - 1;
			if (tmp != 0) {
				break;
			}
		}
		return val;
	}

};

inline std::ostream &operator<<(std::ostream &os, bignum &bn)
{
	std::stringstream ss;
	bignum tmp = bn;
	std::reverse(tmp.data.begin(), tmp.data.end());
	for (auto i : tmp.data)
		ss << std::hex << (int) i;
	os << ss.str();
	return os;
};

#endif /* __AA_BIGNUM_H */
