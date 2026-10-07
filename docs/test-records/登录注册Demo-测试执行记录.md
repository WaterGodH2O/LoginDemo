# 测试执行记录：登录注册 Demo



## 1. 本次执行

| 项    | 内容                    |
| ---- | --------------------- |
| 执行日期 | 2026-10-07            |
| 执行人  | 我自己                   |
| 前端地址 | /                     |
| 账号服务 | http://localhost:5000 |
| 依据   | 测试用例 v1.0             |

## 2. 结果汇总

执行结束后填写数量。

| 项   | 手工  | 接口  |
| --- | --- | --- |
| 通过  |     | 18  |
| 失败  |     | 1   |
| 未执行 |     | 0   |

## 3. 手工执行

### TC-UI-REG-001 用户名为空或只有空格

- [x] 通过
- [ ] 失败

实际结果：同预期

### TC-UI-REG-002 用户名长度不足

- [ ] 通过
- [x] 失败

实际结果：不合法用户名成功注册

### TC-UI-REG-003 注册成功

- [x] 通过
- [ ] 失败

实际结果：同预期

### TC-UI-REG-004 用户名重复

- [x] 通过
- [ ] 失败

实际结果：同预期

### TC-UI-REG-005 密码与确认密码

- [x] 通过
- [ ] 失败

实际结果：同预期

### TC-UI-LOGIN-001 登录信息未填完整

- [x] 通过
- [ ] 失败

实际结果：同预期

### TC-UI-LOGIN-002 凭证正确

- [x] 通过
- [ ] 失败

实际结果：同预期

### TC-UI-LOGIN-003 凭证错误

- [x] 通过
- [ ] 失败

实际结果：同预期

### TC-UI-HOME-001 未登录展示

- [x] 通过
- [ ] 失败

实际结果：同预期

### TC-UI-HOME-002 刷新与退出

- [x] 通过
- [ ] 失败

实际结果：同预期

### TC-UI-NAV-001 注册页与登录页互相进入

- [x] 通过
- [ ] 失败

实际结果：同预期

### TC-UI-NF-001 页面通过接口完成账号操作

- [x] 通过
- [ ] 失败

实际结果：同预期

## 4. 接口执行

### TC-API-REG-001 用户名为空

- [x] 通过
- [ ] 失败

实际结果：HTTP 400，{"message": "请输入用户名"}

### TC-API-REG-002 用户名只有空格

- [x] 通过
- [ ] 失败

实际结果：HTTP 400，{"message": "请输入用户名"}

### TC-API-REG-003 用户名不足 6 位

- [ ] 通过
- [x] 失败

实际结果：注册：HTTP 201，{"message": "注册成功"}。登录：HTTP 200，{"message": "登录成功", "ok": true, "username": "abcde"}

### TC-API-REG-004 用户名刚好 6 位

- [x] 通过
- [ ] 失败

实际结果：HTTP 201，{"message": "注册成功"}

### TC-API-REG-005 用户名重复

- [x] 通过
- [ ] 失败

实际结果：HTTP 409，{"message": "用户名已存在"}

### TC-API-REG-006 重复用户名带首尾空格

- [x] 通过
- [ ] 失败

实际结果：HTTP 409，{"message": "用户名已存在"}

### TC-API-REG-007 密码为空

- [x] 通过
- [ ] 失败

实际结果：HTTP 400，{"message": "请输入密码"}

### TC-API-REG-008 密码按原样保存

- [x] 通过
- [ ] 失败

实际结果：注册：HTTP 201，{"message": "注册成功"}。原样密码登录：HTTP 200，{"message": "登录成功", "ok": true, "username": "spaces"}。去掉空格后登录：HTTP 401，{"message": "用户名或密码错误", "ok": false}

### TC-API-LOGIN-001 用户名为空

- [x] 通过
- [ ] 失败

实际结果：HTTP 400，{"message": "请输入用户名"}

### TC-API-LOGIN-002 用户名只有空格

- [x] 通过
- [ ] 失败

实际结果：HTTP 400，{"message": "请输入用户名"}

### TC-API-LOGIN-003 密码为空

- [x] 通过
- [ ] 失败

实际结果：HTTP 400，{"message": "请输入密码"}

### TC-API-LOGIN-004 凭证正确

- [x] 通过
- [ ] 失败

实际结果：登录：HTTP 200，{"message": "登录成功", "ok": true, "username": "apireg"}。查询登录状态：HTTP 200，{"loggedInAt": "2026-10-07 18:56:30", "ok": true, "username": "apireg"}

### TC-API-LOGIN-005 用户名带首尾空格

- [x] 通过
- [ ] 失败

实际结果：HTTP 200，{"message": "登录成功", "ok": true, "username": "apireg"}

### TC-API-LOGIN-006 用户名不存在

- [x] 通过
- [ ] 失败

实际结果：HTTP 401，{"message": "用户名或密码错误", "ok": false}

### TC-API-LOGIN-007 密码错误

- [x] 通过
- [ ] 失败

实际结果：HTTP 401，{"message": "用户名或密码错误", "ok": false}。用户名不存在时为：HTTP 401，{"message": "用户名或密码错误", "ok": false}

### TC-API-SESSION-001 已登录查询

- [x] 通过
- [ ] 失败

实际结果：第一次：HTTP 200，{"loggedInAt": "2026-10-07 18:56:31", "ok": true, "username": "apireg"}。第二次：HTTP 200，{"loggedInAt": "2026-10-07 18:56:31", "ok": true, "username": "apireg"}

### TC-API-SESSION-002 未登录查询

- [x] 通过
- [ ] 失败

实际结果：HTTP 401，{"message": "未登录", "ok": false}

### TC-API-SESSION-003 退出后查询

- [x] 通过
- [ ] 失败

实际结果：退出：HTTP 200，{"message": "已退出", "ok": true}。再次查询：HTTP 401，{"message": "未登录", "ok": false}

### TC-API-NF-002 重启后账号仍在

- [x] 通过
- [ ] 失败

实际结果：账号服务已重启，健康检查通过。登录：HTTP 200，{"message": "登录成功", "ok": true, "username": "apireg"}
