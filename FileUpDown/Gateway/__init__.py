#!/usr/bin/env python
# encoding: utf-8
"""
This package is used to handle the HTTP request from Restful API URL.
"""


def check_required_parameter(required_list, posted_dict):
    # type: (list, dict) -> list
    """
    Check if any required parameter have not pass by argument dict.
    :param required_list: parameter to be checked
    :param posted_dict: request argument dict
    :return: a list of missed parameter
    """
    ret_list = []
    for p in required_list:
        if p not in posted_dict:
            ret_list.append(p)
    return ret_list
