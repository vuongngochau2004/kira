# RAG Evaluation Report

- Batch ID: `7d62ae4a-9f62-459a-8992-8fe151cd9f6d`
- Total samples: 18
- Successful: 18
- Failed: 0
- Duration: 593.19s

## Aggregate Scores

| Metric | Score |
| --- | ---: |
| answer_relevancy | 0.650 |
| citation_accuracy | 0.944 |
| contextual_precision | 0.224 |
| contextual_recall | 0.278 |
| faithfulness | 0.793 |
| overall_score | 0.565 |
| pass_rate | 0.056 |
| refusal_correctness | 0.500 |

## Samples

### 04_Daotao_1562_QD_BH_Quy_dinh_moi_thinh__chunk_0000_condition_1

- Passed: no
- Overall: 0.572
- Query: Quy định này không được áp dụng với các đối tượng nào?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.833 | yes | The score is 0.83 because the response mostly addresses the question about the regulation's applicability but includes an explanation of the regulation's purpose, which is not directly relevant to the query. |
| faithfulness | 0.600 | no | The score is 0.60 because the actual output incorrectly expands the list of restricted family members to include 'siblings of the spouse,' which is not mentioned in the retrieval context. |
| contextual_precision | 0.000 | no | The score is 0.00 because all five nodes in the retrieval contexts are irrelevant to the input. The first node discusses general university admissions but does not mention specific exclusions. The second node details the Admissions Council's duties, which is unrelated. The third node covers disciplinary actions for exam violations, not exemptions. The fourth node outlines amendments to academic integrity rules, missing the required information. The fifth node mentions lecturers but fails to list the specific exemptions needed. Since no relevant nodes are present, the contextual precision is at its lowest possible score. |
| contextual_recall | 0.000 | no | The score is 0.00 because the expected output lists specific groups of people (Vietnamese residing abroad, foreigners, Party propagandists, law reporters), but none of the nodes in the retrieval context mention these groups. The nodes focus on university admission regulations, exam discipline, and academic integrity, which are unrelated to the expected output. |
| citation_accuracy | 1.000 | yes | Matched 1/1 expected citations. |
| refusal_correctness | 1.000 | yes | The answer did not refuse, as expected. |

### 04_Daotao_1562_QD_BH_Quy_dinh_moi_thinh__chunk_0000_responsibility_2

- Passed: no
- Overall: 0.917
- Query: Đối tượng nào chịu trách nhiệm thi hành Quyết định ban hành quy định mời thỉnh giảng?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.500 | no | The score is 0.50 because the actual output includes several irrelevant statements about sending documents to the Broadcasting Station, reporting to the University of Danang and the University Council, and sending documents to the Board of Directors, which are not directly related to the implementation of the decision. However, the output does address the core question about who is responsible for implementing the decision, preventing the score from being lower. |
| faithfulness | 1.000 | yes | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. The output is perfectly aligned with the provided information—great job! |
| contextual_precision | 1.000 | yes | The score is 1.00 because the first node in the retrieval contexts is highly relevant, explicitly stating the responsible parties for executing the decision, while all subsequent nodes are irrelevant and correctly ranked lower. The irrelevant nodes discuss unrelated topics such as lecture contracts, admissions regulations, and academic integrity, which do not pertain to the query. |
| contextual_recall | 1.000 | yes | The score is 1.00 because the entire expected output is fully supported by the 1st node in the retrieval context, which lists all the responsible parties in the 'Biêu 3' section. |
| citation_accuracy | 1.000 | yes | Matched 1/1 expected citations. |
| refusal_correctness | 1.000 | yes | The answer did not refuse, as expected. |

### 04_Daotao_1562_QD_BH_Quy_dinh_moi_thinh__chunk_0008_fact_1

- Passed: no
- Overall: 0.212
- Query: Mẫu số 9 trong văn bản dùng để báo cáo nội dung gì?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.273 | no | The score is 0.27 because the actual output extensively discusses general reporting regulations, storage requirements, and verification processes, none of which directly address the specific content or purpose of 'Mẫu số 9' as asked in the input. The lack of relevant information about the form's specific use significantly lowers the score. |
| faithfulness | 0.800 | yes | The score is 0.80 because the actual output incorrectly states that the Admissions Council reports to the University of Da Nang (ĐHĐN), while the context specifies that ĐHĐN reports admission results to the Ministry of Education and Training. |
| contextual_precision | 0.200 | no | The score is 0.20 because the retrieval contexts ranked four irrelevant nodes (1st, 2nd, 3rd, and 4th nodes) before the relevant 5th node. The 1st node discusses 'regulations and duties of the Admissions Council', the 2nd node covers 'financial regulations', the 3rd node focuses on 'preserving admission results', and the 4th node outlines 'general regulations of the Admissions Council', none of which mention 'Mẫu số 9'. The 5th node is the only relevant one, as it 'details disciplinary actions... and includes a Minutes of Handling Candidates Violating Academic Integrity Regulations, which corresponds to Mẫu số 9'. |
| contextual_recall | 0.000 | no | The score is 0.00 because the expected output sentence 'Báo cáo kết quả thỉnh giảng tại đơn vị ngoài' is not supported by any nodes in retrieval context, as the contexts focus on 'Báo cáo kết quả tuyển sinh' and other administrative tasks without mentioning 'thỉnh giảng' or 'đơn vị ngoài'. |
| citation_accuracy | 0.000 | no | Matched 0/1 expected citations. |
| refusal_correctness | 0.000 | no | The answer refused even though the sample expects an answer. |

### 04_Daotao_1562_QD_BH_Quy_dinh_moi_thinh__chunk_0008_responsibility_2

- Passed: no
- Overall: 0.350
- Query: Người thỉnh giảng cần cam kết điều gì trong báo cáo kết quả thỉnh giảng?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.600 | no | The score is 0.60 because the output includes irrelevant details about general document content, principles, and admissions processes, which do not address the specific commitments required in the 'Thỉnh giảng' report. However, it partially addresses the query by mentioning relevant sections like 'Definitions' and 'Activities'. |
| faithfulness | 0.500 | no | The score is 0.50 because the actual output incorrectly claims compliance with education and financial regulations, and misrepresents the context's coverage of the student admissions selection process. |
| contextual_precision | 0.000 | no | The score is 0.00 because all five nodes in the retrieval contexts are irrelevant to the input. The first node discusses general regulations and objectives of visiting teaching activities, the second node focuses on the Admissions Council, the third node covers admission criteria, the fourth node details admission result preservation, and the fifth node outlines admission registration procedures. None of these nodes contain the specific commitment a visiting lecturer must make in their report, resulting in a complete lack of relevant information. |
| contextual_recall | 0.000 | no | The score is 0.00 because the sentence in the expected output cannot be attributed to any nodes in the retrieval context. The retrieval context discusses regulations on teaching, recruitment, and admission processes but does not contain any commitment or declaration regarding the accuracy of reports or legal responsibility for misinformation. |
| citation_accuracy | 1.000 | yes | Matched 1/1 expected citations. |
| refusal_correctness | 0.000 | no | The answer refused even though the sample expects an answer. |

### 652_QD_ban_hanh_Quy_che_TS_cac_nganh_dao_chunk_0000_fact_1

- Passed: no
- Overall: 0.893
- Query: Quyết định này thay thế cho văn bản pháp lý nào trước đó?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 1.000 | yes | The score is 1.00 because the actual output is entirely relevant to the input, with no irrelevant statements detected. Great job! |
| faithfulness | 0.857 | yes | The score is 0.86 because the actual output incorrectly states that Decision No. 1248/QĐ-ĐHĐN promulgates the current regulations, while the retrieval context clarifies that it was replaced by Decision No. 1478/QĐ-ĐHĐN, making it the previous regulation instead. |
| contextual_precision | 0.500 | no | The score is 0.50 because the second node in the retrieval contexts, which directly answers the input question, is ranked lower than the first irrelevant node. The first node discusses amendments to 'Academic Integrity Regulations' and references Decision 29/QĐ-ĐHBK/2017, which is unrelated to the query about replacing a specific admission regulation. The third, fourth, and fifth nodes are also irrelevant, as they focus on disciplinary actions, Admissions Council duties, and penalties for academic dishonesty, respectively. The score is not higher because the relevant node is not ranked first among the retrieval contexts. |
| contextual_recall | 1.000 | yes | The score is 1.00 because the entire expected output is fully supported by the 2nd node in the retrieval context, which explicitly mentions the exact decision number, date, and content in Article 2. Perfect match! |
| citation_accuracy | 1.000 | yes | Matched 1/1 expected citations. |
| refusal_correctness | 1.000 | yes | The answer did not refuse, as expected. |

### 652_QD_ban_hanh_Quy_che_TS_cac_nganh_dao_chunk_0000_responsibility_2

- Passed: no
- Overall: 0.889
- Query: Đối tượng nào chịu trách nhiệm thi hành Quyết định này?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 1.000 | yes | The score is 1.00 because the actual output is entirely relevant and directly addresses the input without any irrelevant statements. Great job! |
| faithfulness | 1.000 | yes | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. The output is perfectly aligned with the provided information—great job! |
| contextual_precision | 0.333 | no | The score is 0.33 because the only relevant node is ranked third, while the first, second, fourth, and fifth nodes are irrelevant. The first node 'contains general regulations' but does not explicitly list the specific individuals responsible for executing the Decision. The second node is an 'internal processing form' with metadata but no specific article detailing the responsible subjects. The fourth node discusses the 'composition and duties of the Admissions Council' but does not specify responsibility for executing the Decision. The fifth node details the 'organization and duties of the Admissions Council' but lacks the clause assigning execution responsibility. The third node is the only one that 'contains the full text of the Decision' and explicitly states the responsible subjects, making it the sole relevant node. |
| contextual_recall | 1.000 | yes | The score is 1.00 because the entire expected output is perfectly matched by the 3rd node in the retrieval context, which explicitly lists the same responsible parties. |
| citation_accuracy | 1.000 | yes | Matched 1/1 expected citations. |
| refusal_correctness | 1.000 | yes | The answer did not refuse, as expected. |

### 652_QD_ban_hanh_Quy_che_TS_cac_nganh_dao_chunk_0010_responsibility_1

- Passed: no
- Overall: 0.917
- Query: Cơ sở đào tạo có trách nhiệm gì trong việc giải quyết đơn thư phản ánh, khiếu nại, tố cáo liên quan đến công tác tuyển sinh?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 1.000 | yes | The score is 1.00 because the actual output is entirely relevant and directly addresses the input question without any irrelevant statements. Great job! |
| faithfulness | 0.500 | no | The score is 0.50 because the actual output incorrectly attributes the responsibility for resolving admission-related complaints and violations to the Admission Council of the training facility, while the context clearly states that this authority lies with the Admission Council of ĐHĐN (HĐTS ĐHĐN). |
| contextual_precision | 1.000 | yes | The score is 1.00 because all relevant nodes are ranked higher than the irrelevant node. The first four nodes in the retrieval contexts directly address the responsibility for resolving complaints, while the fifth node, which focuses on admission registration methods and reporting results, is ranked last. |
| contextual_recall | 1.000 | yes | The score is 1.00 because the entire expected output is perfectly supported by the 1st node in the retrieval context, which contains the exact same information. |
| citation_accuracy | 1.000 | yes | Matched 1/1 expected citations. |
| refusal_correctness | 1.000 | yes | The answer did not refuse, as expected. |

### 652_QD_ban_hanh_Quy_che_TS_cac_nganh_dao_chunk_0010_responsibility_2

- Passed: yes
- Overall: 1.000
- Query: Ai là người có thẩm quyền xem xét và quyết định việc điều chỉnh, bổ sung, sửa đổi Quy chế trong quá trình thực hiện?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 1.000 | yes | The score is 1.00 because the actual output is entirely relevant and directly addresses the input without any irrelevant statements. Great job! |
| faithfulness | 1.000 | yes | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. The output is perfectly aligned with the provided information—great job! |
| contextual_precision | 1.000 | yes | The score is 1.00 because the first node in the retrieval contexts directly answers the input question, while all subsequent nodes are irrelevant and correctly ranked lower. The first node explicitly states that the Director of the University has the authority to adjust, supplement, or amend the regulation, making it the most relevant. The other nodes focus on administrative details, the Admissions Council's duties, the admission process, or amendments to a different sub-regulation, none of which address the specific question about the authority to amend the main regulation. |
| contextual_recall | 1.000 | yes | The score is 1.00 because the entire expected output 'Giám đốc ĐHĐN' is fully supported by the 1st node in the retrieval context, which explicitly mentions this phrase in the text: 'Việc điều chỉnh do Giám đốc ĐHĐN xem xét, quyết định...'. Perfect match! |
| citation_accuracy | 1.000 | yes | Matched 1/1 expected citations. |
| refusal_correctness | 1.000 | yes | The answer did not refuse, as expected. |

### no_answer_001

- Passed: no
- Overall: 0.567
- Query: Các văn bản này có quy định mức học phí cho năm 2099 là bao nhiêu không?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.571 | no | The score is 0.57 because the actual output includes irrelevant information about 2026 admission regulations, academic integrity, and payment deadlines, which do not address the specific query about 2099 tuition fees. However, the score is not lower because the output may still contain some relevant details or context related to tuition fees. |
| faithfulness | 0.833 | yes | The score is 0.83 because the actual output incorrectly states that the regulations apply to the 'University of Technology' (Trường Đại học Bách khoa), while the retrieval context specifies they apply to the 'University of Danang' and its member universities. |
| contextual_precision | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Precision' metric |
| contextual_recall | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Recall' metric |
| citation_accuracy | 1.000 | yes | No expected citations were defined for this sample. |
| refusal_correctness | 1.000 | yes | The answer correctly refused due to missing evidence. |

### no_answer_002

- Passed: no
- Overall: 0.361
- Query: Có văn bản nào nêu lịch nghỉ Tết năm 2099 của Trường Đại học Bách khoa không?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.333 | no | The score is 0.33 because the actual output discusses multiple unrelated topics (academic integrity, student assessment, PhD training, and undergraduate admissions) instead of addressing the Tet holiday schedule for 2099. These irrelevant statements significantly lower the score, though the score is not zero due to some partial relevance or structure in the response. |
| faithfulness | 0.833 | yes | The score is 0.83 because the actual output incorrectly specifies that Decision No. 1478/QĐ-ĐHĐN is for the 'full-time undergraduate level', while the context only mentions it is about 'admission regulations' without specifying the level. |
| contextual_precision | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Precision' metric |
| contextual_recall | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Recall' metric |
| citation_accuracy | 1.000 | yes | No expected citations were defined for this sample. |
| refusal_correctness | 0.000 | no | The answer should have refused but attempted to answer. |

### no_answer_003

- Passed: no
- Overall: 0.333
- Query: Các tài liệu này có công bố danh sách mật khẩu tài khoản sinh viên không?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 1.000 | yes | The score is 1.00 because the actual output directly addresses the input question without any irrelevant statements. It provides a clear and focused response, demonstrating high relevancy. |
| faithfulness | 0.000 | no | Evaluation LLM outputted an invalid JSON. Please use a better evaluation model. |
| contextual_precision | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Precision' metric |
| contextual_recall | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Recall' metric |
| citation_accuracy | 1.000 | yes | No expected citations were defined for this sample. |
| refusal_correctness | 0.000 | no | The answer should have refused but attempted to answer. |

### no_answer_004

- Passed: no
- Overall: 0.381
- Query: Có quy định nào trong các tài liệu này yêu cầu sinh viên mua một mẫu laptop cụ thể không?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.286 | no | The score is 0.29 because the actual output contains multiple irrelevant statements about admission regulations, exam violations, and academic integrity, which are unrelated to the specific question about laptop requirements. These off-topic details significantly lower the relevancy of the response. |
| faithfulness | 1.000 | yes | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. The output is perfectly aligned with the provided information—great job! |
| contextual_precision | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Precision' metric |
| contextual_recall | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Recall' metric |
| citation_accuracy | 1.000 | yes | No expected citations were defined for this sample. |
| refusal_correctness | 0.000 | no | The answer should have refused but attempted to answer. |

### no_answer_005

- Passed: no
- Overall: 0.595
- Query: Các văn bản này có nêu điểm chuẩn tuyển sinh năm 2099 không?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.714 | yes | The score is 0.71 because the actual output includes irrelevant details about general admission regulations and the roles of admission councils, which do not address the specific query about 2099 admission scores. However, the score is not lower because the output likely contains some relevant information or context related to the query. |
| faithfulness | 0.857 | yes | The score is 0.86 because the actual output incorrectly referred to the document as a draft, while the retrieval context clearly states it is an official 'Regulation on university-level admission' issued under Decision No. /QĐ-ĐHĐN. |
| contextual_precision | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Precision' metric |
| contextual_recall | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Recall' metric |
| citation_accuracy | 1.000 | yes | No expected citations were defined for this sample. |
| refusal_correctness | 1.000 | yes | The answer correctly refused due to missing evidence. |

### no_answer_006

- Passed: no
- Overall: 0.500
- Query: Các văn bản này có quy định mức học phí cho năm 2099 là bao nhiêu không?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.333 | no | The score is 0.33 because the actual output contains multiple irrelevant statements about admission regulations, textbook compilation, academic assessment, and disciplinary actions, none of which address the input's question about tuition fees for the year 2099. This lack of relevance significantly lowers the score, but it is not zero because the output may still contain some partially relevant information or context. |
| faithfulness | 0.667 | no | The score is 0.67 because the actual output incorrectly refers to 'regulations on assessing learning results' instead of the correct 'regulations on midterm and final exams' (Decision 202/QĐ-ĐHBK), and conflates separate decisions on academic integrity and exam regulations, which are distinct in the retrieval context. |
| contextual_precision | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Precision' metric |
| contextual_recall | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Recall' metric |
| citation_accuracy | 1.000 | yes | No expected citations were defined for this sample. |
| refusal_correctness | 1.000 | yes | The answer correctly refused due to missing evidence. |

### no_answer_007

- Passed: no
- Overall: 0.400
- Query: Có văn bản nào nêu lịch nghỉ Tết năm 2099 của Trường Đại học Bách khoa không?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.400 | no | The score is 0.40 because the actual output includes multiple irrelevant statements about academic integrity regulations, student learning assessment, and admission regulations, which do not address the query about the Tet holiday schedule for 2099. However, the score is not lower because the output may have partially acknowledged the query context. |
| faithfulness | 1.000 | yes | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. The output is perfectly aligned with the provided information—great job! |
| contextual_precision | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Precision' metric |
| contextual_recall | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Recall' metric |
| citation_accuracy | 1.000 | yes | No expected citations were defined for this sample. |
| refusal_correctness | 0.000 | no | The answer should have refused but attempted to answer. |

### no_answer_008

- Passed: no
- Overall: 0.417
- Query: Các tài liệu này có công bố danh sách mật khẩu tài khoản sinh viên không?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.500 | no | The score is 0.50 because the actual output discusses unrelated topics like staff accounts, software permissions, and general academic regulations, which do not address the specific question about the publication of student passwords. |
| faithfulness | 1.000 | yes | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. The output is perfectly aligned with the provided information—great job! |
| contextual_precision | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Precision' metric |
| contextual_recall | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Recall' metric |
| citation_accuracy | 1.000 | yes | No expected citations were defined for this sample. |
| refusal_correctness | 0.000 | no | The answer should have refused but attempted to answer. |

### no_answer_009

- Passed: no
- Overall: 0.417
- Query: Có quy định nào trong các tài liệu này yêu cầu sinh viên mua một mẫu laptop cụ thể không?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.500 | no | The score is 0.50 because the actual output includes irrelevant statements about textbook compilation and admission regulations, which do not address the laptop requirement question. However, the score is not lower because the output may still contain some relevant information, though it is overshadowed by the irrelevant content. |
| faithfulness | 1.000 | yes | The score is 1.00 because there are no contradictions between the actual output and the retrieval context. The output is perfectly aligned with the provided information—great job! |
| contextual_precision | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Precision' metric |
| contextual_recall | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Recall' metric |
| citation_accuracy | 1.000 | yes | No expected citations were defined for this sample. |
| refusal_correctness | 0.000 | no | The answer should have refused but attempted to answer. |

### no_answer_010

- Passed: no
- Overall: 0.448
- Query: Các văn bản này có nêu điểm chuẩn tuyển sinh năm 2099 không?

| Metric | Score | Pass | Reason |
| --- | ---: | --- | --- |
| answer_relevancy | 0.857 | yes | The score is 0.86 because the response includes general information about the Admissions Council's duties and powers, which is not directly relevant to the specific query about admission scores for the year 2099. However, the response is largely focused on the topic, preventing a lower score. |
| faithfulness | 0.833 | yes | The score is 0.83 because the actual output incorrectly attributes the decision of passing scores to the Admissions Council, while the context clarifies that it is determined by the University of Da Nang and must meet current regulations. |
| contextual_precision | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Precision' metric |
| contextual_recall | 0.000 | no | 'expected_output' cannot be None for the 'Contextual Recall' metric |
| citation_accuracy | 1.000 | yes | No expected citations were defined for this sample. |
| refusal_correctness | 0.000 | no | The answer should have refused but attempted to answer. |
