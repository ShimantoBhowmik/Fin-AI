# React Chat Frontend

This project is a React-based chat application that interacts with a backend API built with Python (FastAPI/Flask). The application features a chat interface for sending and receiving messages, a response panel for displaying backend responses, and a visualization component for showing status updates.

## Features

- Chat interface for real-time messaging
- Response panel to display messages from the backend
- Status visualization to represent backend updates
- Modular components for easy maintenance and scalability



Can you make the frontend more beautiful? Like the left side panel should be like a chat like interface. The status updates that are returned from backend should be displayed there.
The status updates look like this : 

╰─λ curl -X POST http://localhost:8000/analyze \                                                    (base) 0 (17.617s) < 10:23:57
          -H "Content-Type: application/json" \
          -d '{"query": "Give me analysis for $AAPL"}'
event: analysis_start
data: {"query": "Give me analysis for $AAPL", "timestamp": "2025-08-03T10:24:58.475069"}

event: status_update
data: {"step":"ticker_extraction","status":"processing","message":"Extracting stock ticker from your query...","progress":0.1,"data":null}

event: status_update
data: {"step":"ticker_extraction","status":"completed","message":"Found ticker: AAPL","progress":0.2,"data":{"ticker":"AAPL"}}

event: status_update
data: {"step":"browser_initialization","status":"processing","message":"Initializing browser for data extraction...","progress":0.25,"data":null}

event: status_update
data: {"step":"browser_initialization","status":"completed","message":"Browser initialized successfully","progress":0.3,"data":null}

event: status_update
data: {"step":"fundamentals_extraction","status":"processing","message":"Extracting fundamental data for AAPL...","progress":0.35,"data":null}


And the final response should be displayed on a right hand panel and it usually looks like : 

data: {"step":"report_generation","status":"completed","message":"Report generated successfully","progress":1.0,"data":{"report":{"ticker":"AAPL","company_name":"AAPL","timestamp":"2025-08-03T10:27:21.844767","query":"Give me analysis for $AAPL","price_info":{"current_price":207.57,"change":-5.19,"change_percent":-2.58},"analysis":"<think>\nHmm, the user wants me to create a detailed financial report for AAPL in Markdown format based on their structured data inputs. They've provided fundamentals data, news items, and reddit sentiment information.\n\nLooking at the fundamentals section, I can see this is Apple Inc. with current price of $207.57, experiencing a slight decline of 2.58%. The P/E ratio is 30.66, market cap is about $3 trillion, trading volume was high today but average volume suggests normalcy.\n\nThe news section shows several articles from Yahoo Finance dated August 3rd, mostly about financial planning and some mentioning equities/yields. There's an earnings date listed though - I should note that since the specific date isn't provided.\n\nFor reddit sentiment, it's neutral with a very low confidence score of just 0.15/1.0. The key issue is they couldn't analyze any substantive posts about AAPL because there weren't enough relevant comments or tags to work with. This makes sense given that many Reddit discussions might not have been captured.\n\nThe user probably wants this information presented professionally and clearly, perhaps for investment decisions or analysis purposes. They seem organized since they've provided structured data but want it formatted in Markdown for easier reading and sharing. \n\nI'll create a comprehensive report following the specified format: fundamentals overview with key metrics in a table, latest news summary with bullet points, reddit sentiment section highlighting the limitations of their input data, overall market outlook providing context without speculation, and a final summary tying everything together.\n\nThe challenge here is that some data seems incomplete (like earnings date) so I'll make sure to point this out. For the neutral sentiment from Reddit, I should be clear about what limited information was available rather than creating false analysis.\n</think>\n```markdown\n# Financial Report: Apple Inc. (AAPL)\n\n## 1. Fundamentals Overview\n\nApple Inc. (AAPL) is a leading global technology company known for its innovative products and services. The following table provides key metrics from the given data:\n\n| Metric             | Value                  |\n|--------------------|-------------------------|\n| **Ticker**         | AAPL                    |\n| **Current Price**  | $207.57                 |\n| **Change Today**   | -$5.19 (-2.58%)          |\n| **P/E Ratio**      | 30.66                   |\n| **Market Capitalization** | ~$3.0 Trillion         |\n\n### Additional Notes:\n- The stock experienced a slight decline of $5.19 or -2.58% on August 3rd.\n- Trading volume was notably high today ($97,203,859) compared to the average daily volume ($53,580,620).\n\n## 2. Latest News Summary\n\nHere is a summary of the top news items related to Apple (AAPL):\n\n### - Financial Planning and Tax Strategies\n1. **Earnings Date:** While an earnings date was noted in the fundamentals, no specific details were provided.\n2. **IRA Contributions and RMD Taxes:** An article discussed whether converting IRA contributions to Roth accounts could reduce taxes on required minimum distributions (RMDs). This topic is relevant for investors concerned with tax implications of their holdings.\n\n### - Equities Market Insights\n3. **Focus on Yields Decline:** The market experienced a decline in yields following certain economic reports or events, which may impact long-term growth expectations.\n4. **Healthcare Retirement Planning:** Guidance was offered for individuals with substantial retirement savings (e.g., $1 million) to plan healthcare costs effectively.\n\n### - Advertisements\n5. **IRA and Roth Accounts:** Multiple advertisements targeted individuals seeking advice on managing retirement accounts through Roth conversions or other strategies, aligning with topics relevant to long-term investors holding Apple stock.\n\n## 3. Reddit Sentiment Analysis\n\nThe provided input for Reddit sentiment analysis indicates the following:\n\n- **Overall Sentiment:** Neutral.\n- **Confidence Score:** Very low (0.15/1.0).\n- **Analysis Limitation:** The text contained no substantive posts or comments related to AAPL stock, preventing meaningful sentiment analysis.\n\n### Key Discussion Points:\nThe absence of relevant content makes it impossible to draw insights about investor opinions on Apple's performance or prospects from Reddit discussions. Further data is required for accurate sentiment assessment.\n\n## 4. Overall Market Outlook\n\nApple Inc. (AAPL) continues to be a cornerstone of the technology sector, with its fundamentals reflecting strong market presence and financial health as evidenced by its significant market capitalization and trading activity. The neutral Reddit sentiment suggests that there isn't sufficient public discussion data at this time to gauge investor opinion accurately.\n\nThe latest news focuses on broader topics such as tax planning for retirement savings and general equities market conditions, which may indirectly influence Apple's stock performance but do not provide specific catalysts or directional insights about the company itself.\n\n## 5. Final Summary\n\nApple Inc. (AAPL) is currently trading at $207.57 with a slight decrease of -2.58% on August 3rd. The P/E ratio of 30.66 indicates that investors are valuing Apple based on future earnings expectations, while its market cap remains among the largest globally.\n\nThe news section highlights ongoing interest in financial planning strategies for retirement savings, including tax-efficient approaches like Roth conversions and RMD management. These topics may be relevant to long-term holders of AAPL but do not directly impact the company's operations or stock price without further context linking them explicitly.\n\nReddit sentiment analysis is constrained by insufficient relevant content; no substantive discussions about AAPL were provided for analysis.\n```","fundamentals":{"previous_close":207.57,"open":210.89,"days_range":"201.50 - 213.58","volume":97203859,"avg_volume":53580620,"market_cap":3003000000000.0,"beta":5.0,"pe_ratio":30.66,"target_est":232.63,"earnings_date":"Earnings Date","fifty_two_week_range":null},"reddit_sentiment":{"sentiment":"neutral","confidence":0.15,"summary":"Unable to analyze sentiment due to lack of relevant content. The text contains no discussion points related to AAPL."},"news":[{"title":"I Have $1.5M: Should I Convert $120K/Year to Roth & Avoid Up To 50% Tax On RMD? (Ask an Advisor)Ask An AdvisorFinance Advisors   .   AdAd","source":"Yahoo Finance","url":"https://trk.financeadvisors.com/997b3684-2ca1-4e8c-9674-21d7802c1b5f","date":"2025-08-03"},{"title":"A Public Company Just Went All-In on Solana—Here’s Why It MattersThis isn’t a side project. This is a full-scale pivot.bullseyealerts   .   AdAd","source":"Yahoo Finance","url":"https://confantentedited.com/ad01e2d8-e302-4e5f-b70c-848c0b02d6fa","date":"2025-08-03"},{"title":"$1.5M IRA at 67: Should You Convert $120K/Yr to Roth & Reduce RMD Taxes Up to 50%? (Ask an Advisor)Ask An AdvisorFinance Advisors   .   AdAd","source":"Yahoo Finance","url":"https://trk.financeadvisors.com/997b3684-2ca1-4e8c-9674-21d7802c1b5f","date":"2025-08-03"},{"title":"How Savvy Investors Pay for Healthcare in RetirementIf you have $1 million, get this guide to help prepare for healthcare costs in retirement.Fisher Investments   .   AdAd","source":"Yahoo Finance","url":"https://www.fisherinvestments.com/en-us/campaigns/hphc/he","date":"2025-08-03"},{"title":"","source":"Yahoo Finance","url":"https://finance.yahoo.com/news/equities-yields-tumble-following-jobs-211518896.html","date":"2025-08-03"}]}}}


And all of this should be treamed in the frontend

## Project Structure

```
react-chat-frontend
├── src
│   ├── components
│   │   ├── Chat
│   │   ├── Panel
│   │   ├── Visualization
│   │   └── Layout
│   ├── services
│   ├── types
│   ├── hooks
│   ├── App.tsx
│   └── index.tsx
├── public
│   └── index.html
├── package.json
├── tsconfig.json
└── README.md
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   ```

2. Navigate to the project directory:
   ```
   cd react-chat-frontend
   ```

3. Install the dependencies:
   ```
   npm install
   ```

## Usage

1. Start the development server:
   ```
   npm start
   ```

2. Open your browser and navigate to `http://localhost:3000` to view the application.

## API Integration

The frontend interacts with the backend API through the `src/services/api.ts` file, which contains functions for fetching and updating queries. Ensure that your backend is running and accessible for the frontend to function correctly.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.