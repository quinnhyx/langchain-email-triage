# 1. counters 初始化
action_count = 0
category_count = 0
priority_count = 0

# 2. evaluation_results 初始化
evaluation_results = []

# 3. for loop
    # analyze email
    # 更新三个 accuracy counter
    # 保存完整 evaluation result
for case in test_cases:
    email = case["email"]
    result = analyze_email(email)

    category_count += 1 if result.category == case["expected_category"] else 0
    action_count += 1 if result.action == case["expected_action"] else 0
    priority_count += 1 if result.priority == case["expected_priority"] else 0

    evaluation_results.append({
        "email": email,
        "expected_category": case["expected_category"],
        "predicted_category": result.category,
        "expected_action": case["expected_action"],
        "predicted_action": result.action,
        "expected_priority": case["expected_priority"],
        "predicted_priority": result.priority
    })

# 4. 三个 accuracy
category_accuracy = category_count / len(test_cases)
action_accuracy = action_count / len(test_cases)
priority_accuracy = priority_count / len(test_cases)

# 5. 转 DataFrame
df = pd.DataFrame(evaluation_results)
# 6. confusion matrix
confusion_matrix = pd.crosstab(df["expected_action"], df["predicted_action"])

# 7. critical errors
critical_errors = df[
    (df["expected_action"] == "reply") &
    (df["predicted_action"] == "ignore")
]

# 8. print results
print("Confusion Matrix:\n", confusion_matrix)
print("Critical Errors:\n", critical_errors)